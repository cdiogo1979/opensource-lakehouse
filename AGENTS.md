# Project guide for agents

This is a lakehouse **data product repository**. [README.md](README.md) is the complete guide: how runs work, the workflow JSON reference, the entry-point and config contracts, Jupyter, CI, and limits. Read it before changing anything. This file lists only the rules agents must follow.

## What belongs here
- `workflows/<name>.json`: Airflow DAG declarations (workflow JSON v1, see the README). This is the only way to declare DAGs.
- `notebooks/workload/*.py`: Spark entry points in Jupytext `py:percent` format, runnable by `spark-submit` and as notebooks.
- `notebooks/common/`: shared helpers (`config_loader.py`, `cli.py`, `job_runtime.py`), used by Airflow runs and Jupyter, and the Jupyter `%run` scripts `jupyter_environment_resolver.py` and `jupyter_input_widget_helper.py`.
- `configs/<env>.yml` and optional `configs/<product>/<env>.yml`: non-secret settings for `prod`, `uat`, `dev`.
- `dags/lakehouse.py`: the platform stub. **Never edit it, and never add files to `dags/`.**
- `requirements.txt`: optional extra Python packages for the workload code, installed by the platform at each Airflow run and with `lakehouse-install-requirements` in Jupyter.
- `tests/`, `scripts/code_quality.sh`, `Jenkinsfile`, `requirements-dev.txt`.

## Rules
- **No DAG code**: don't write Airflow DAG code, operators, or a DAG factory here. The lakehouse platform's `lakehouse_dags` package builds the DAGs from `workflows/*.json`. DAG IDs are `<bundle>-<name>` and must not be set or changed in this repository.
- **Valid workflows**: keep every workflow file valid. One invalid file blocks all of the bundle's DAGs in Airflow. CI runs `lakehouse-validate-workflows .`. Unknown fields are refused, `name` must equal the file name, and `entrypoint` must exist in `notebooks/workload/`.
- **Entry points**:
  - use `notebooks.common.job_runtime.start_spark_job(app_name)` for the config and the Spark session, and declare task arguments for `notebooks.common.cli.parse_task_args(...)` (workflow `args` after `--` in Airflow, widgets or `TASK_ARGS` in Jupyter; values are strings, never templated; check them in the job);
  - never configure Spark catalogs, tokens or redaction here: the platform's `lakehouse_spark` does that;
  - structure every notebook in `notebooks/workload/` as: title, `## Initialization`, `## Imports`, the job's own sections, `## Execution` (only the `__main__` block); a test checks it;
  - start every notebook in `notebooks/workload/` with the Initialization section (after the title cell): `# !lakehouse-install-requirements ~/work/opensource-lakehouse` and `# %run ../common/jupyter_environment_resolver.py`; use `jupyter_input_widget_helper.py` after `WIDGET_LIST` for task arguments;
  - keep run code under `if __name__ == "__main__":` and stop Spark in `finally:`.
- **Configs**:
  - the loader accepts only `dev`, `uat` and `prod`, requires `storage_path` and `database_name`, and never falls back across environments;
  - values must be the product's own namespaces and buckets;
  - no credentials, tokens, or endpoints anywhere in the repository.
- **Dependencies**:
  - Airflow, Spark, PySpark and Python versions belong to the platform; don't pin or install them here.
  - Entry points run on the platform's Python 3.10 set (PyYAML, requests, pandas, numpy, pyarrow, ...) plus `requirements.txt`.
  - `requirements.txt` holds only plain, pinned requirements (`name==version`): no pip options, URLs, paths, or `pyspark`/`py4j`/`pip`/`setuptools`/`wheel`. Every package must have a CPython 3.10 Linux aarch64 wheel for glibc 2.31 or older, and must not need a different version of a platform package. CI (`lakehouse-validate-workflows .`) checks this.
  - Test tools go in `requirements-dev.txt`.
- **Python style**: Google-style docstrings on new functions, Black and Ruff with line length 200, Flake8 and Bandit clean (`scripts/code_quality.sh all`).
- **Keep the docs current**: update `README.md`, and this file if a rule changes, whenever the layout or a contract changes.
- **AI-DLC work**: follow `.agents/skills/aidlc-workflows/SKILL.md`; artifacts live in `aidlc-docs/`.
