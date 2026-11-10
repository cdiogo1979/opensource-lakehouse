# Project guide for agents

This is a lakehouse **data product repository**. [README.md](README.md) is the complete guide: how runs work, the workflow JSON reference, the entry-point and config contracts, Jupyter, CI, and limits. Read it before changing anything. This file lists only the rules agents must follow.

## What belongs here
- `workflows/<project>/<name>.json`: Airflow DAG declarations (workflow JSON v1, see the README), grouped by subproject. This is the only way to declare DAGs.
- `notebooks/workload/<project>/` (and its layer folders `bronze/`, `silver/`, `gold/`, `ops/`, `deploy/`, `other/`): the subproject's Spark entry points in Jupytext `py:percent` format, runnable by `spark-submit` and as notebooks.
- `notebooks/common/`: shared helpers (`config_loader.py`, `cli.py`, `job_runtime.py`), used by Airflow runs and Jupyter, and the Jupyter `%run` scripts `jupyter_environment_resolver.py` and `jupyter_input_widget_helper.py`.
- `configs/<env>.yml` and optional `configs/<product>/<env>.yml`: non-secret settings for `prod`, `uat`, `dev`.
- `dags/lakehouse.py`: the platform stub. **Never edit it, and never add files to `dags/`.**
- `requirements.txt`: optional extra Python packages for the workload code, installed by the platform at each Airflow run and with `lakehouse-install-requirements` in Jupyter.
- `tests/`, `scripts/code_quality.sh`, `Jenkinsfile`, `requirements-dev.txt`.
- `aidlc-docs/current/`: the active AI-DLC intent's documents, stage artifacts, `aidlc-state.md` and `audit.md`, until the intent closes.
- `aidlc-docs/knowledge/`: canonical, current facts that carry across intents:
  - `aidlc-docs/knowledge/<project>/application-design.md`: the subproject's architecture;
  - `aidlc-docs/knowledge/<project>/functional-design/<component>.md`: one consolidated functional design per component (business logic, rules, domain entities).
- `aidlc-docs/archive/<intent-id>/`: immutable snapshots and summaries of closed intents. Never edit archived history.

## Subproject layout
Every subproject has a folder with the **same name** under `workflows/` and `notebooks/workload/` (and, for AI-DLC work, under `aidlc-docs/knowledge/`). For example, subproject `sample` uses:

```text
workflows/
└── sample/
    ├── test_environment.json
    └── generate_tpch.json
notebooks/
├── common/                 shared by every subproject
└── workload/
    └── sample/
        ├── bronze/                  raw ingestion
        ├── silver/                  cleaned or conformed data
        ├── gold/                    curated, consumption-ready data
        ├── ops/                     operational notebooks run as needed
        ├── deploy/                  deployment of assets the pipelines don't create
        └── other/                   notebooks that fit no medallion layer
            ├── test_environment.py
            ├── count_sample_rows.py
            └── generate_tpch.py
aidlc-docs/knowledge/
└── sample/
    ├── application-design.md
    └── functional-design/
```

- **Layers** (notebooks only; workflows are grouped by subproject only): put each new notebook in the layer folder that matches its role:
  - `bronze/` for raw ingestion, `silver/` for cleaned or conformed data, `gold/` for curated, consumption-ready data;
  - `ops/` for operational notebooks run as needed (data migrations, data patching, other maintenance), not part of the medallion pipeline; describe prerequisites and execution considerations in the title cell;
  - `deploy/` for notebooks that deploy or update assets the pipelines don't create (for example views); describe the target assets and deployment assumptions in the title cell;
  - `other/` for notebooks that fit none of the above, such as `sample`'s smoke-table, row-count and TPC-H notebooks.

  These six are the only folders, one level deep. The platform also accepts a notebook directly in the subproject folder, but put each notebook in the folder that matches its role.
- **Entry points**: a workflow in `workflows/<project>/` names a notebook of `notebooks/workload/<project>/` in its `entrypoint`: for example `other/generate_tpch.py` or `bronze/load_orders.py` (a file directly in the folder is named without a folder). The platform runs `notebooks/workload/<project>/<entrypoint>` and refuses other folders.
- **Names**: DAG IDs are `<bundle>-<name>`, without the subproject, so a workflow name must be unique across all subprojects of this repository; CI refuses a repeated name.
- **New subproject**: create both folders together, with lowercase letters, digits, `_` or `-` in the name; nothing goes directly into `workflows/` or `notebooks/workload/` (a test checks it). Shared code stays in `notebooks/common/`; configuration in `configs/`.
- **Expected artifacts** when adding or changing a workload, updated together: the notebook in `notebooks/workload/<project>/`, its workflow in `workflows/<project>/` when it is scheduled or orchestrated, environment values in `configs/`, and its tests. Use names that make clear which notebook and settings a workflow uses.
- **Durable design knowledge** (AI-DLC): one application design per subproject and one consolidated functional design per component under `aidlc-docs/knowledge/<project>/`; drafts and approvals stay in `aidlc-docs/current/` and are promoted at intent closure, with the originals archived.

## Rules
- **No DAG code**: don't write Airflow DAG code, operators, or a DAG factory here. The lakehouse platform's `lakehouse_dags` package builds the DAGs from `workflows/*.json`. DAG IDs are `<bundle>-<name>` and must not be set or changed in this repository.
- **Valid workflows**: keep every workflow file valid. One invalid file blocks all of the bundle's DAGs in Airflow. CI runs `lakehouse-validate-workflows .`. Unknown fields are refused, `name` must equal the file name and be unique in the repository, and `entrypoint` must exist in `notebooks/workload/<project>/`.
- **Entry points**:
  - use `notebooks.common.job_runtime.start_spark_job(app_name)` for the config and the Spark session, and declare task arguments for `notebooks.common.cli.parse_task_args(...)` (workflow `args` after `--` in Airflow, widgets or `TASK_ARGS` in Jupyter; values are strings, never templated; check them in the job);
  - never configure Spark catalogs, tokens or redaction here: the platform's `lakehouse_spark` does that;
  - structure every notebook in `notebooks/workload/<project>/` as: title, `## Initialization`, `## Imports`, the job's own sections, `## Execution` (only the `__main__` block); a test checks it;
  - start every notebook in `notebooks/workload/<project>/` with the Initialization section (after the title cell): `# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp` and `# %run ../../../common/jupyter_environment_resolver.py` (from a layer folder; `../../common/...` for a notebook directly in the subproject folder); use `jupyter_input_widget_helper.py` after `WIDGET_LIST` for task arguments;
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
- **Keep the docs current**: update `README.md`, and this file if a rule changes, whenever the layout or a contract changes. Whenever a notebook changes, revise its title cell so it describes the notebook's current purpose, inputs and effects.
- **AI-DLC work**: follow `.agents/skills/aidlc-workflows/SKILL.md`; artifacts live in `aidlc-docs/`.
