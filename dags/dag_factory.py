"""Build standard Spark workload DAGs from minimal workload metadata."""

import hashlib
import json
import logging
import os
import re
import ssl
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import docker
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

from dag_defaults import identity_for_bundle, standard_dag_kwargs
from spark_output import redact_spark_output

DAGS_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = DAGS_DIR.parent
CONFIG_DIR = BUNDLE_ROOT / "configs"
CONTAINER_BUNDLE_ROOT = Path("/opt/lakehouse-bundle")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SparkWorkload:
    """Normalized workload entry used to construct submit tasks."""

    task_name: str
    entrypoint_file: str
    runs_after: tuple[str, ...]


def _validate_environment_config(environment: str, config_dir: str) -> None:
    """Validate the bundle version's environment YAML before Spark startup.

    Args:
        environment: Environment selected by the current Git bundle name.
        config_dir: Config directory from the parsed bundle version.
    """
    sys.path.insert(0, str(BUNDLE_ROOT / "notebooks" / "common"))
    from config_loader import load_environment_config

    load_environment_config(environment, config_dir)


def _normalize_workloads(workloads: Sequence[Mapping[str, Any]]) -> tuple[SparkWorkload, ...]:
    """Validate workload declarations and their task dependency graph.

    Args:
        workloads: Workload mappings with task name, entrypoint, and optional
            predecessor task names.

    Returns:
        Validated workloads in declaration order.

    Raises:
        ValueError: If declarations are invalid, dependencies are unknown, or
            the dependency graph contains a cycle.
        FileNotFoundError: If an entrypoint file is missing from the bundle.
    """
    if not workloads:
        raise ValueError("At least one Spark workload entrypoint is required.")

    normalized = []
    allowed_keys = {"task_name", "entrypoint_file", "runs_after"}
    for declaration in workloads:
        if not isinstance(declaration, Mapping):
            raise ValueError("Each workload must be a mapping with task_name and entrypoint_file fields.")
        unknown_keys = set(declaration) - allowed_keys
        if unknown_keys:
            raise ValueError(f"Unknown workload fields: {', '.join(sorted(unknown_keys))}")

        task_name = declaration.get("task_name")
        entrypoint_file = declaration.get("entrypoint_file")
        raw_dependencies = declaration.get("runs_after", ())
        if not isinstance(task_name, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]+", task_name):
            raise ValueError(f"Invalid Spark workload task name: {task_name!r}")
        if not isinstance(entrypoint_file, str):
            raise ValueError(f"Invalid Python entrypoint for workload {task_name!r}.")
        if Path(entrypoint_file).name != entrypoint_file or not entrypoint_file.endswith(".py"):
            raise ValueError("Each entrypoint must be a Python filename in notebooks/workload/.")
        if raw_dependencies is None:
            dependencies = ()
        elif isinstance(raw_dependencies, str):
            dependencies = (raw_dependencies,)
        elif isinstance(raw_dependencies, Sequence):
            dependencies = tuple(raw_dependencies)
        else:
            raise ValueError(f"runs_after for workload {task_name!r} must be a task name or sequence.")
        if any(not isinstance(dependency, str) for dependency in dependencies):
            raise ValueError(f"runs_after for workload {task_name!r} must contain task names.")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError(f"runs_after for workload {task_name!r} contains duplicate task names.")

        workload_path = BUNDLE_ROOT / "notebooks" / "workload" / entrypoint_file
        if not workload_path.is_file():
            raise FileNotFoundError(f"Spark workload entrypoint does not exist: {workload_path}")
        normalized.append(SparkWorkload(task_name, entrypoint_file, dependencies))

    task_names = {workload.task_name for workload in normalized}
    if len(task_names) != len(normalized):
        raise ValueError("Spark workload task names must be unique.")
    for workload in normalized:
        unknown_dependencies = set(workload.runs_after) - task_names
        if unknown_dependencies:
            raise ValueError(f"Workload {workload.task_name!r} runs after unknown tasks: " f"{', '.join(sorted(unknown_dependencies))}.")
        if workload.task_name in workload.runs_after:
            raise ValueError(f"Workload {workload.task_name!r} cannot run after itself.")

    resolved = set()
    unresolved = {workload.task_name: set(workload.runs_after) for workload in normalized}
    while unresolved:
        ready = {name for name, dependencies in unresolved.items() if dependencies <= resolved}
        if not ready:
            raise ValueError("Spark workload runs_after dependencies contain a cycle.")
        resolved.update(ready)
        for name in ready:
            del unresolved[name]

    return tuple(normalized)


def _container_name(dag_id: str, run_id: str) -> str:
    """Build a stable, Docker-safe container name for one DAG run.

    Args:
        dag_id: Airflow DAG identifier.
        run_id: Unique identifier for the DAG run.

    Returns:
        A Docker container name unique to the DAG run.
    """
    safe_dag_id = re.sub(r"[^a-zA-Z0-9_.-]", "-", dag_id)
    run_suffix = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
    return f"lakehouse-{safe_dag_id[:40]}-{run_suffix}"


def _docker_host_bundle_path(bundle_source: str) -> str:
    """Translate an Airflow-container bundle path to its Docker-host path.

    Args:
        bundle_source: Versioned bundle root as seen inside the Airflow
            scheduler container.

    Returns:
        The same bundle revision under the host-mounted bundle root.

    Raises:
        AirflowException: If the bundle path is outside the configured
            container root or either root is missing or invalid.
    """
    host_root_value = os.environ.get("LAKEHOUSE_BUNDLE_HOST_ROOT")
    container_root_value = os.environ.get("LAKEHOUSE_BUNDLE_CONTAINER_ROOT")
    if not host_root_value or not container_root_value:
        raise AirflowException("LAKEHOUSE_BUNDLE_HOST_ROOT and LAKEHOUSE_BUNDLE_CONTAINER_ROOT must be configured.")

    host_root = Path(host_root_value)
    container_root = Path(container_root_value)
    if not host_root.is_absolute() or not container_root.is_absolute():
        raise AirflowException("Airflow bundle host and container roots must be absolute paths.")

    resolved_bundle = Path(bundle_source).resolve()
    resolved_container_root = container_root.resolve()
    try:
        relative_bundle = resolved_bundle.relative_to(resolved_container_root)
    except ValueError as error:
        raise AirflowException("The versioned DAG bundle path is outside LAKEHOUSE_BUNDLE_CONTAINER_ROOT.") from error

    return str(host_root / relative_bundle)


def _read_broker_control_token() -> str:
    """Read the scheduler-only broker control credential without logging it."""
    path = Path(os.environ.get("AIRFLOW_BROKER_CONTROL_TOKEN_FILE", "/run/secrets/airflow_broker_control_token"))
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AirflowException("The broker control credential is unavailable.") from error
    if len(token) < 32:
        raise AirflowException("The broker control credential is invalid.")
    return token


def _broker_request(method: str, route: str, payload: Mapping[str, Any] | None, credential: str) -> dict[str, Any] | None:
    """Call the private broker using verified TLS and sanitized failures.

    Args:
        method: HTTP method.
        route: Versioned broker route, with no credential in the URL.
        payload: Optional JSON request body.
        credential: Control token or run-scoped capability; never logged.

    Returns:
        Parsed JSON response, or ``None`` for an empty success response.

    Raises:
        AirflowException: If the broker request fails or returns an invalid body.
    """
    base_url = os.environ.get("LAKEHOUSE_BROKER_URL", "https://airflow-token-broker:8443").rstrip("/")
    parsed_base_url = urlsplit(base_url)
    if (
        parsed_base_url.scheme != "https"
        or parsed_base_url.hostname != "airflow-token-broker"
        or parsed_base_url.port != 8443
        or parsed_base_url.path
        or parsed_base_url.query
        or parsed_base_url.fragment
        or parsed_base_url.username
        or parsed_base_url.password
    ):
        raise AirflowException("The token broker endpoint is not the approved private HTTPS service.")
    ca_file = os.environ.get("LAKEHOUSE_BROKER_CA_FILE", "/run/certs/airflow-token-broker-ca.crt")
    try:
        context = ssl.create_default_context(cafile=ca_file)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{base_url}{route}",
            data=body,
            headers={"Authorization": f"Bearer {credential}", "Accept": "application/json", "Content-Type": "application/json"},
            method=method,
        )
        with urlopen(request, context=context, timeout=5) as response:
            raw = response.read()
        return json.loads(raw) if raw else None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        raise AirflowException("The token broker request failed; sensitive response details were suppressed.") from None


def _create_spark_container(
    image: str,
    network: str,
    data_network: str,
    docker_url: str,
    bundle_source: str,
    bundle_target: str,
    environment: str,
    aws_region: str,
    broker_ca_host_path: str,
    broker_ca_container_path: str,
    **context: object,
) -> dict[str, str]:
    """Start one reusable Spark container and mount the DAG bundle into it.

    Args:
        image: Spark image containing ``spark-submit`` and its dependencies.
        network: Optional Docker network for lakehouse services.
        docker_url: Docker daemon URL.
        bundle_source: Host path to this versioned bundle checkout.
        bundle_target: Container path where the bundle is mounted.
        environment: Selected lakehouse environment.
        aws_region: AWS-compatible region passed to Spark applications.
        **context: Airflow task context, including the DAG and run IDs.

    Returns:
        The container name for downstream submit and cleanup tasks.
    """
    dag_id = context["dag"].dag_id
    container_name = _container_name(dag_id, str(context["run_id"]))
    docker_bundle_source = _docker_host_bundle_path(bundle_source)
    control_token = _read_broker_control_token()
    registration = _broker_request(
        "POST",
        "/v1/runs",
        {"dag_id": dag_id, "run_id": str(context["run_id"])},
        control_token,
    )
    if not isinstance(registration, dict):
        raise AirflowException("The token broker returned an invalid registration response.")
    run_handle = registration.get("run_handle")
    capability = registration.get("renewal_capability")
    initial_token = registration.get("access_token")
    if not all(isinstance(value, str) and value for value in (run_handle, capability, initial_token)):
        raise AirflowException("The token broker returned an incomplete registration response.")

    volumes = {
        docker_bundle_source: {"bind": bundle_target, "mode": "ro"},
        broker_ca_host_path: {"bind": broker_ca_container_path, "mode": "ro"},
    }
    client = docker.DockerClient(base_url=docker_url)
    container = None
    try:
        try:
            client.containers.get(container_name).remove(force=True)
        except docker.errors.NotFound:
            pass

        container = client.containers.create(
            image=image,
            command=["sleep infinity"],
            name=container_name,
            network=network,
            entrypoint=["/bin/bash", "-lc"],
            labels={"lakehouse-local.role": "airflow-spark-run", "lakehouse-local.run-handle": run_handle},
            environment={
                "AWS_REGION": aws_region,
                "AWS_DEFAULT_REGION": aws_region,
                "AWS_EC2_METADATA_DISABLED": "true",
                "LAKEHOUSE_TOKEN_PROVIDER": "airflow",
                "LAKEHOUSE_INITIAL_ACCESS_TOKEN": initial_token,
                "LAKEHOUSE_TOKEN_BROKER_URL": os.environ.get("LAKEHOUSE_BROKER_URL", "https://airflow-token-broker:8443"),
                "LAKEHOUSE_TOKEN_BROKER_CA": broker_ca_container_path,
                "LAKEHOUSE_RUN_HANDLE": run_handle,
                "LAKEHOUSE_RUN_CAPABILITY": capability,
                "SPARK_CONTAINER_ROLE": "driver",
                "SPARK_MASTER_HOST": "spark",
                "LAKEHOUSE_ENVIRONMENT": environment,
                "PYTHONPATH": bundle_target,
            },
            volumes=volumes,
        )
        client.networks.get(data_network).connect(container)
        container.start()
        LOGGER.info("Started reusable Spark container %s for DAG run %s", container_name, context["run_id"])
        return {"container_name": container.name, "run_handle": run_handle}
    except Exception:
        if container is not None:
            try:
                container.remove(force=True)
            except docker.errors.DockerException:
                LOGGER.warning("Failed Spark container cleanup after startup error.")
        try:
            _broker_request("DELETE", f"/v1/runs/{quote(run_handle, safe='')}", None, control_token)
        except AirflowException:
            LOGGER.warning("Broker run revocation failed after Spark startup error; bounded expiry remains active.")
        raise
    finally:
        client.close()


def _submit_spark_job(
    entrypoint_file: str,
    environment: str,
    config_path: str,
    docker_url: str,
    spark_master: str,
    **context: object,
) -> None:
    """Run one Spark application inside the container created for this DAG run.

    Args:
        entrypoint_file: Python job path relative to the bundle root.
        environment: Selected lakehouse environment.
        config_path: Environment YAML path inside the Spark container.
        docker_url: Docker daemon URL.
        spark_master: Spark master URL; defaults to local mode.
        **context: Airflow task context, including task instance and DAG run.

    Raises:
        AirflowException: If ``spark-submit`` exits with a non-zero status.
    """
    task_instance = context["ti"]
    run_state = task_instance.xcom_pull(task_ids="create_cluster")
    container_name = run_state.get("container_name") if isinstance(run_state, dict) else None
    if not container_name:
        raise AirflowException("The Spark container was not registered for this DAG run.")

    container_entrypoint = CONTAINER_BUNDLE_ROOT / "notebooks" / "workload" / entrypoint_file
    command = [
        "/opt/spark/bin/spark-submit",
        "--master",
        spark_master,
        "--files",
        config_path,
        str(container_entrypoint),
        "--environment",
        environment,
        "--config-dir",
        "spark-files",
    ]

    client = docker.DockerClient(base_url=docker_url)
    try:
        container = client.containers.get(container_name)
        result = container.exec_run(command, workdir=str(CONTAINER_BUNDLE_ROOT), demux=False)
        if result.exit_code != 0:
            LOGGER.error("Spark workload %s failed; sanitized output follows:\n%s", entrypoint_file, redact_spark_output(result.output or b""))
            raise AirflowException(f"spark-submit for {entrypoint_file} exited with status {result.exit_code}.")
    finally:
        client.close()


def _stop_spark_container(docker_url: str, **context: object) -> None:
    """Stop and remove this DAG run's Spark container, including after failures.

    Args:
        docker_url: Docker daemon URL.
        **context: Airflow task context, including the DAG and run IDs.
    """
    container_name = _container_name(context["dag"].dag_id, str(context["run_id"]))
    run_state = context["ti"].xcom_pull(task_ids="create_cluster") or {}
    run_handle = run_state.get("run_handle") if isinstance(run_state, dict) else None
    cleanup_errors = []
    client = docker.DockerClient(base_url=docker_url)
    try:
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            LOGGER.info("Spark container %s is already absent.", container_name)
        else:
            try:
                container.remove(force=True)
                LOGGER.info("Stopped and removed Spark container %s.", container_name)
            except docker.errors.DockerException:
                cleanup_errors.append("container")
    finally:
        client.close()
    if isinstance(run_handle, str) and run_handle:
        try:
            control_token = _read_broker_control_token()
            _broker_request("DELETE", f"/v1/runs/{quote(run_handle, safe='')}", None, control_token)
        except AirflowException:
            cleanup_errors.append("broker")
    if cleanup_errors:
        raise AirflowException("Airflow writer-run cleanup was incomplete; broker expiry remains the fallback.")
    task_instances = context["dag_run"].get_task_instances()
    failed_workloads = sorted(task.task_id for task in task_instances if task.task_id.startswith("submit_") and task.state == "failed")
    if failed_workloads:
        raise AirflowException(f"Spark workload task(s) failed: {', '.join(failed_workloads)}.")


def create_spark_dag(
    dag_name: str,
    workloads: Sequence[Mapping[str, Any]],
    schedule: str | None,
) -> DAG:
    """Create a standard config-validation and reusable Spark-container DAG.

    Args:
        dag_name: Name used in the Airflow DAG ID and description.
        workloads: Ordered mappings with ``task_name`` and ``entrypoint_file``;
            optional ``runs_after`` names predecessor tasks. Entrypoint files
            may repeat. Workloads without predecessors run in parallel.
        schedule: Airflow schedule; pass ``None`` for manual-only execution.

    Returns:
        A DAG with config validation, container lifecycle, and submit tasks.

    Raises:
        ValueError: If a workload declaration or dependency graph is invalid.
        FileNotFoundError: If a workload file is missing.
    """
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", dag_name):
        raise ValueError(f"Invalid DAG name: {dag_name!r}")
    normalized_workloads = _normalize_workloads(workloads)

    dag_id_prefix, environment = identity_for_bundle(DAGS_DIR)
    workload_names = [workload.task_name for workload in normalized_workloads]
    config_path = CONFIG_DIR / f"{environment}.yml"
    container_config_path = str(CONTAINER_BUNDLE_ROOT / config_path.relative_to(BUNDLE_ROOT))
    spark_job_image = os.environ.get("LAKEHOUSE_SPARK_IMAGE", "airflow-spark-job:3.5.5_1.8.1")
    spark_master = os.environ.get("LAKEHOUSE_SPARK_MASTER", "local[*]")
    docker_url = os.environ.get("LAKEHOUSE_DOCKER_URL", "unix://var/run/docker.sock")
    docker_network = os.environ.get("LAKEHOUSE_SPARK_DOCKER_NETWORK")
    data_network = os.environ.get("LAKEHOUSE_SPARK_DATA_NETWORK", "lakehouse-local_data-access")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    broker_ca_host_path = os.environ.get("LAKEHOUSE_BROKER_CA_HOST_PATH", "")
    broker_ca_container_path = os.environ.get("LAKEHOUSE_BROKER_CA_CONTAINER_PATH", "/run/certs/airflow-token-broker-ca.crt")
    if not docker_network or not Path(broker_ca_host_path).is_absolute():
        raise AirflowException("The Spark networks and broker CA mount must be configured.")

    dag = DAG(
        **standard_dag_kwargs(
            environment=environment,
            workload_name=dag_name,
            description=(f"Run {dag_name} using {', '.join(workload_names)} in one Spark container " f"for the {environment} bundle environment."),
            schedule=schedule,
            tags=("spark",),
            dag_id_prefix=dag_id_prefix,
        )
    )
    validate_environment = PythonOperator(
        task_id="validate_environment",
        python_callable=_validate_environment_config,
        op_kwargs={"environment": environment, "config_dir": str(CONFIG_DIR)},
        dag=dag,
    )
    create_cluster = PythonOperator(
        task_id="create_cluster",
        python_callable=_create_spark_container,
        op_kwargs={
            "image": spark_job_image,
            "network": docker_network,
            "data_network": data_network,
            "docker_url": docker_url,
            "bundle_source": str(BUNDLE_ROOT),
            "bundle_target": str(CONTAINER_BUNDLE_ROOT),
            "environment": environment,
            "aws_region": aws_region,
            "broker_ca_host_path": broker_ca_host_path,
            "broker_ca_container_path": broker_ca_container_path,
        },
        dag=dag,
    )

    submit_tasks = {}
    for workload in normalized_workloads:
        submit_task = PythonOperator(
            task_id=f"submit_{workload.task_name}",
            python_callable=_submit_spark_job,
            op_kwargs={
                "entrypoint_file": workload.entrypoint_file,
                "environment": environment,
                "config_path": container_config_path,
                "docker_url": docker_url,
                "spark_master": spark_master,
            },
            dag=dag,
        )
        submit_tasks[workload.task_name] = submit_task

    stop_cluster = PythonOperator(
        task_id="stop_cluster",
        python_callable=_stop_spark_container,
        op_kwargs={"docker_url": docker_url},
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag,
    )

    validate_environment >> create_cluster
    for workload in normalized_workloads:
        submit_task = submit_tasks[workload.task_name]
        if workload.runs_after:
            for predecessor in workload.runs_after:
                submit_tasks[predecessor] >> submit_task
        else:
            create_cluster >> submit_task
        submit_task >> stop_cluster
    return dag
