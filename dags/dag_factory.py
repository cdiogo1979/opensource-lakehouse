"""Build standard Spark workload DAGs from minimal workload metadata."""

import hashlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Sequence

import docker
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

from dag_defaults import identity_for_bundle, standard_dag_kwargs

DAGS_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = DAGS_DIR.parent
CONFIG_DIR = BUNDLE_ROOT / "configs"
CONTAINER_BUNDLE_ROOT = Path("/opt/lakehouse-bundle")
LOGGER = logging.getLogger(__name__)


def _validate_environment_config(environment: str, config_dir: str) -> None:
    """Validate the bundle version's environment YAML before Spark startup.

    Args:
        environment: Environment selected by the current Git bundle name.
        config_dir: Config directory from the parsed bundle version.
    """
    sys.path.insert(0, str(BUNDLE_ROOT / "notebooks" / "common"))
    from config_loader import load_environment_config

    load_environment_config(environment, config_dir)


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


def _create_spark_container(
    image: str,
    network: str | None,
    docker_url: str,
    bundle_source: str,
    bundle_target: str,
    environment: str,
    aws_region: str,
    **context: object,
) -> str:
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
    client = docker.DockerClient(base_url=docker_url)
    try:
        try:
            client.containers.get(container_name).remove(force=True)
        except docker.errors.NotFound:
            pass

        container = client.containers.run(
            image=image,
            command=["/bin/sh", "-c", "while true; do sleep 3600; done"],
            name=container_name,
            network=network,
            detach=True,
            environment={
                "AWS_REGION": aws_region,
                "AWS_DEFAULT_REGION": aws_region,
                "LAKEHOUSE_ENVIRONMENT": environment,
                "PYTHONPATH": bundle_target,
            },
            volumes={bundle_source: {"bind": bundle_target, "mode": "ro"}},
        )
        LOGGER.info("Started reusable Spark container %s for DAG run %s", container_name, context["run_id"])
        return container.name
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
    container_name = task_instance.xcom_pull(task_ids="create_cluster")
    if not container_name:
        container_name = _container_name(context["dag"].dag_id, str(context["run_id"]))

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
        output = result.output or b""
        LOGGER.info("Spark output for %s:\n%s", entrypoint_file, output.decode(errors="replace"))
        if result.exit_code != 0:
            raise AirflowException(
                f"spark-submit for {entrypoint_file} exited with status {result.exit_code}."
            )
    finally:
        client.close()


def _stop_spark_container(docker_url: str, **context: object) -> None:
    """Stop and remove this DAG run's Spark container, including after failures.

    Args:
        docker_url: Docker daemon URL.
        **context: Airflow task context, including the DAG and run IDs.
    """
    container_name = _container_name(context["dag"].dag_id, str(context["run_id"]))
    client = docker.DockerClient(base_url=docker_url)
    try:
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            LOGGER.info("Spark container %s is already absent.", container_name)
            return

        container.remove(force=True)
        LOGGER.info("Stopped and removed Spark container %s.", container_name)
    finally:
        client.close()


def create_spark_dag(workloads: Sequence[tuple[str, str]], schedule: str | None) -> DAG:
    """Create a standard config-validation and reusable Spark-container DAG.

    Args:
        workloads: Ordered ``(task_name, entrypoint_file)`` pairs. Entrypoint
            files may repeat; each named workload is submitted sequentially to
            the same Spark container.
        schedule: Airflow schedule; pass ``None`` for manual-only execution.

    Returns:
        A DAG with config validation, container lifecycle, and submit tasks.

    Raises:
        ValueError: If a task name is invalid or a job entrypoint is not a
            simple Python filename.
        FileNotFoundError: If any workload file is missing.
    """
    if not workloads:
        raise ValueError("At least one Spark workload entrypoint is required.")
    task_names = [task_name for task_name, _ in workloads]
    if len(set(task_names)) != len(task_names):
        raise ValueError("Spark workload task names must be unique.")

    for task_name, entrypoint_file in workloads:
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", task_name):
            raise ValueError(f"Invalid Spark workload task name: {task_name!r}")
        if Path(entrypoint_file).name != entrypoint_file or not entrypoint_file.endswith(".py"):
            raise ValueError("Each entrypoint must be a Python filename in notebooks/workload/.")
        workload_path = BUNDLE_ROOT / "notebooks" / "workload" / entrypoint_file
        if not workload_path.is_file():
            raise FileNotFoundError(f"Spark workload entrypoint does not exist: {workload_path}")

    dag_id_prefix, environment = identity_for_bundle(DAGS_DIR)
    workload_names = [task_name for task_name, _ in workloads]
    workload_group_name = "-".join(workload_names)
    config_path = CONFIG_DIR / f"{environment}.yml"
    container_config_path = str(CONTAINER_BUNDLE_ROOT / config_path.relative_to(BUNDLE_ROOT))
    spark_job_image = os.environ.get("LAKEHOUSE_SPARK_IMAGE", "airflow-spark-job:3.5.5_1.8.1")
    spark_master = os.environ.get("LAKEHOUSE_SPARK_MASTER", "local[*]")
    docker_url = os.environ.get("LAKEHOUSE_DOCKER_URL", "unix://var/run/docker.sock")
    docker_network = os.environ.get("LAKEHOUSE_SPARK_DOCKER_NETWORK")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    dag = DAG(
        **standard_dag_kwargs(
            environment=environment,
            workload_name=workload_group_name,
            description=(
                f"Run {', '.join(workload_names)} sequentially in one Spark container "
                f"for the {environment} bundle environment."
            ),
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
            "docker_url": docker_url,
            "bundle_source": str(BUNDLE_ROOT),
            "bundle_target": str(CONTAINER_BUNDLE_ROOT),
            "environment": environment,
            "aws_region": aws_region,
        },
        dag=dag,
    )

    submit_tasks = []
    for task_name, entrypoint_file in workloads:
        submit_task = PythonOperator(
            task_id=f"submit_{task_name}",
            python_callable=_submit_spark_job,
            op_kwargs={
                "entrypoint_file": entrypoint_file,
                "environment": environment,
                "config_path": container_config_path,
                "docker_url": docker_url,
                "spark_master": spark_master,
            },
            dag=dag,
        )
        submit_tasks.append(submit_task)

    stop_cluster = PythonOperator(
        task_id="stop_cluster",
        python_callable=_stop_spark_container,
        op_kwargs={"docker_url": docker_url},
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag,
    )

    validate_environment >> create_cluster
    previous_task = create_cluster
    for submit_task in submit_tasks:
        previous_task >> submit_task
        previous_task = submit_task
    previous_task >> stop_cluster
    return dag
