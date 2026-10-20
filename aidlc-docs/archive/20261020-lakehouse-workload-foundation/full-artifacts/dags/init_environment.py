"""Declare the Airflow DAG entrypoint, Spark job, and schedule for this branch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dag_factory import create_spark_dag  # noqa: E402

dag = create_spark_dag(
    entrypoint_file="init_environment.py",
    schedule=None,
)
# test4
