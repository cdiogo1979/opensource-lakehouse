"""Build standard Spark workload DAGs from minimal workload metadata."""

import os
import sys
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

from dag_defaults import identity_for_bundle, standard_dag_kwargs

DAGS_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = DAGS_DIR.parent
CONFIG_DIR = BUNDLE_ROOT / "configs"
CONTAINER_BUNDLE_ROOT = Path("/opt/lakehouse-bundle")


def _validate_environment_config(environment: str, config_dir: str) -> None:
    """Validate the bundle version's environment YAML before Spark submission.

    Args:
        environment: Environment selected by the current Git bundle name.
        config_dir: Config directory from the parsed bundle version.
    """
    sys.path.insert(0, str(BUNDLE_ROOT / "notebooks" / "common"))
    from config_loader import load_environment_config

    load_environment_config(environment, config_dir)


def create_spark_dag(entrypoint_file: str, schedule: str | None) -> DAG:
    """Create the standard config-validation and Docker Spark submission DAG.

    Args:
        entrypoint_file: Python job file under ``notebooks/workload/``.
        schedule: Airflow schedule; pass ``None`` for manual-only execution.

    Returns:
        A DAG with the standard validation and Spark submission tasks.

    Raises:
        ValueError: If the entrypoint is not a simple Python filename.
        FileNotFoundError: If the workload file is missing.
    """
    if Path(entrypoint_file).name != entrypoint_file or not entrypoint_file.endswith(".py"):
        raise ValueError("entrypoint_file must be a Python filename in notebooks/workload/")

    dag_id_prefix, environment = identity_for_bundle(DAGS_DIR)
    workload_name = Path(entrypoint_file).stem
    workload_path = BUNDLE_ROOT / "notebooks" / "workload" / entrypoint_file
    if not workload_path.is_file():
        raise FileNotFoundError(f"Spark workload entrypoint does not exist: {workload_path}")

    config_path = CONFIG_DIR / f"{environment}.yml"
    container_config_path = CONTAINER_BUNDLE_ROOT / config_path.relative_to(BUNDLE_ROOT)
    container_workload_path = CONTAINER_BUNDLE_ROOT / workload_path.relative_to(BUNDLE_ROOT)
    spark_job_image = os.environ.get("LAKEHOUSE_SPARK_IMAGE", "airflow-spark-job:3.5.5_1.8.1")
    spark_master = os.environ.get("LAKEHOUSE_SPARK_MASTER", "local[*]")
    docker_url = os.environ.get("LAKEHOUSE_DOCKER_URL", "unix://var/run/docker.sock")
    docker_network = os.environ.get("LAKEHOUSE_SPARK_DOCKER_NETWORK")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    dag = DAG(
        **standard_dag_kwargs(
            environment=environment,
            workload_name=workload_name,
            description=(f"Manually run the {workload_name} Spark workload " f"for the {environment} bundle environment."),
            schedule=schedule,
            tags=("spark",),
            dag_id_prefix=dag_id_prefix,
        )
    )
    validate_environment = PythonOperator(
        task_id="validate_environment_config",
        python_callable=_validate_environment_config,
        op_kwargs={"environment": environment, "config_dir": str(CONFIG_DIR)},
        dag=dag,
    )
    submit_spark_job = DockerOperator(
        task_id=f"submit_{workload_name}",
        image=spark_job_image,
        command=[
            "/opt/spark/bin/spark-submit",
            "--master",
            spark_master,
            "--files",
            str(container_config_path),
            str(container_workload_path),
            "--environment",
            environment,
            "--config-dir",
            "spark-files",
        ],
        container_name=f"{environment}-{workload_name.replace('_', '-')}",
        docker_url=docker_url,
        network_mode=docker_network,
        environment={
            "AWS_REGION": aws_region,
            "AWS_DEFAULT_REGION": aws_region,
            "PYTHONPATH": str(CONTAINER_BUNDLE_ROOT),
        },
        mounts=[
            Mount(
                target=str(CONTAINER_BUNDLE_ROOT),
                source=str(BUNDLE_ROOT),
                type="bind",
                read_only=True,
            )
        ],
        mount_tmp_dir=False,
        auto_remove="success",
        retries=1,
        dag=dag,
    )
    validate_environment >> submit_spark_job
    return dag
