# Project guide for agents

This is a lakehouse **data product repository**. [README.md](README.md) is the complete guide: how runs work, the workflow JSON reference, the entry-point and config contracts, Jupyter, CI, and limits. Read it before changing anything. This file lists only the rules agents must follow.

## What belongs here
- `workflows/<name>.json`: Airflow DAG declarations (workflow JSON v1, see the README). This is the only way to declare DAGs.
- `notebooks/workload/*.py`: Spark entry points in Jupytext `py:percent` format, runnable by `spark-submit` and as notebooks.
- `notebooks/common/`: shared helpers (`config_loader.py`, `cli.py`, `job_runtime.py`), used by Airflow runs and Jupyter.
- `configs/<env>.yml` and optional `configs/<product>/<env>.yml`: non-secret settings for `prod`, `uat`, `dev`.
- `dags/lakehouse.py`: the platform stub. **Never edit it, and never add files to `dags/`.**
- `tests/`, `scripts/code_quality.sh`, `Jenkinsfile`, `requirements-dev.txt`.

## Rules
- **No DAG code**: don't write Airflow DAG code, operators, or a DAG factory here. The lakehouse platform's `lakehouse_dags` package builds the DAGs from `workflows/*.json`. DAG IDs are `<bundle>-<name>` and must not be set or changed in this repository.
- **Valid workflows**: keep every workflow file valid. One invalid file blocks all of the bundle's DAGs in Airflow. CI runs `lakehouse-validate-workflows .`. Unknown fields are refused, `name` must equal the file name, and `entrypoint` must exist in `notebooks/workload/`.
- **Entry points**:
  - use `notebooks.common.job_runtime.start_spark_job(app_name)` for the config and the Spark session, and `notebooks.common.cli.task_args()` for workflow `args` (passed after `--`, never templated);
  - keep run code under `if __name__ == "__main__":` and stop Spark in `finally:`.
- **Configs**:
  - the loader accepts only `dev`, `uat` and `prod`, requires `storage_path` and `database_name`, and never falls back across environments;
  - values must be the product's own namespaces and buckets;
  - no credentials, tokens, or endpoints anywhere in the repository.
- **Dependencies**: Airflow, Spark and provider versions belong to the platform; don't pin or install them here. Entry points can use only what the platform's Spark image provides. Test tools go in `requirements-dev.txt`.
- **Python style**: Google-style docstrings on new functions, Black and Ruff with line length 200, Flake8 and Bandit clean (`scripts/code_quality.sh all`).
- **Keep the docs current**: update `README.md`, and this file if a rule changes, whenever the layout or a contract changes.
- **AI-DLC work**: follow `.agents/skills/aidlc-workflows/SKILL.md`; artifacts live in `aidlc-docs/`.
