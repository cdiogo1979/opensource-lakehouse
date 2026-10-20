"""Declare this branch's Spark workloads and Airflow schedule."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dag_factory import create_spark_dag  # noqa: E402

dag = create_spark_dag(
    workloads=(
        ("initialize_environment_first", "init_environment.py"),
        ("initialize_environment_second", "init_environment.py"),
    ),
    schedule=None,
)
