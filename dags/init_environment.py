"""Declare this branch's Spark workloads and Airflow schedule."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dag_factory import create_spark_dag  # noqa: E402

dag = create_spark_dag(
    dag_name="init_environment",
    workloads=(
        {
            "task_name": "initialize_environment_first",
            "entrypoint_file": "init_environment.py",
        },
        {
            "task_name": "initialize_environment_second",
            "entrypoint_file": "init_environment.py",
            "runs_after": ("initialize_environment_first",),
        },
        {
            "task_name": "count_sample_rows",
            "entrypoint_file": "count_sample_rows.py",
            "runs_after": ("initialize_environment_first",),
        },
    ),
    schedule=None,
)
