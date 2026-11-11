# Open Source Lakehouse Workloads

This repository is a **data product repository**. It holds a product's Spark code, its environment settings, and the declarations of its Airflow workflows. It doesn't hold any DAG-building logic, infrastructure, or credentials: the lakehouse platform turns the workflow declarations into Airflow DAGs, runs them in Spark containers, and gives each run its product's write credentials.

The same code runs in two places:
- **Airflow**: scheduled or manual runs of the production (`main`) and UAT (`uat`) branches.
- **Jupyter**: interactive development with the `dev` settings.

**Contents**
1. [What lives where](#what-lives-where)
2. [How a run works](#how-a-run-works)
3. [Repository layout](#repository-layout)
4. [Workflow JSON reference](#workflow-json-reference)
5. [The DAG stub](#the-dag-stub)
6. [Writing an entry point](#writing-an-entry-point)
7. [Python packages](#python-packages)
8. [Configs and environments](#configs-and-environments)
9. [Working in Jupyter](#working-in-jupyter)
10. [CI in Jenkins](#ci-in-jenkins)
11. [The tpch subproject](#the-tpch-subproject)
12. [How-to](#how-to)
13. [Limits](#limits)

## What lives where

| This repository | The lakehouse platform |
|---|---|
| `workflows/<project>/*.json`: which DAGs exist, their tasks, order, schedule, arguments, retries and timeouts | Turning each workflow into an Airflow DAG (the `lakehouse_dags` factory) |
| `notebooks/workload/<project>/*.py`: the Spark jobs, also usable as notebooks | Starting one Spark container per DAG run, with this repository mounted read-only |
| `notebooks/common/`: config loading, argument parsing, Spark session start-up | Issuing the product's short-lived write token to each run, through the token broker |
| `configs/`: non-secret settings per environment (storage path, catalog, database) | The Git bundles that Airflow reads from this repository (`<product>-main`, `<product>-uat`) |
| `dags/lakehouse.py`: a fixed two-line stub | The Jenkins jobs that check this repository, and the workflow validator they use |
| `requirements.txt` (optional): extra Python packages for this repository's code | The shared Python 3.10 environment (pandas, numpy, pyarrow, PyYAML, requests, ...) and the lock that pins it, the same in Airflow and Jupyter |

Nothing in this repository holds a password, key, or token, and nothing should.

## How a run works

1. **Bundles**: the platform's data product file names this repository in its `repo` block. Airflow then keeps two Git bundles of it:
   - `<product>-main` tracks the production branch (`main` for `default`) and runs in environment `prod`;
   - `<product>-uat` tracks the UAT branch (`uat`) and runs in environment `uat`.

   Each bundle checks out `dags/`, `workflows/`, `notebooks/`, `configs/` and the files at the repository root (such as `requirements.txt`), and refreshes about every 5 minutes.
2. **DAGs**: Airflow parses `dags/lakehouse.py`, which asks the platform to build one DAG per `workflows/<name>.json`. The DAG ID is `<bundle>-<name>`, for example `default-uat-test_environment`. The platform's token broker relies on that prefix to pick the product's writer, so DAG IDs are never chosen in this repository.
3. **Each DAG has the same fixed shape**:

   ```text
   create_cluster ─▶ install_requirements ─▶ validate_environment ─▶ submit_<task> … (in runs_after order) ─▶ stop_cluster ─▶ verify_workloads_succeeded
   ```

   - `create_cluster` registers the run with the token broker and starts one Spark container. The container mounts the run's exact bundle commit at `/opt/lakehouse-bundle`, read-only.
   - `install_requirements` installs this repository's `requirements.txt` into the container, constrained by the platform's lock (see [Python packages](#python-packages)). Without a `requirements.txt` it does nothing. It retries twice, 30 seconds apart; if it still fails, no task runs.
   - `validate_environment` loads the environment's config inside that container with this repository's own `notebooks/common/config_loader.py`.
   - Each `submit_<task>` runs one entry point with `spark-submit --master local[*]` as its own Spark application. Tasks without `runs_after` start together; the others wait for their predecessors.
   - `stop_cluster` always runs, even after failures. It removes the container and revokes the run's token.
   - `verify_workloads_succeeded` succeeds only if every task succeeded.
4. **Credentials**: the container gets only a short-lived token for the product's writer user and a way to renew it during the run. Spark reads and writes Iceberg tables through the Polaris catalog, and the storage credentials come from Polaris. Everything a run does is within the product's own namespaces and buckets.
5. **Versions**: code, configs and workflows always come from the same commit, the one recorded for that run.

## Repository layout

```text
workflows/                 One JSON file per Airflow DAG (see the reference below), per subproject
  sample/                    subproject "sample"
    test_environment.json      the smoke table: create twice, then count
    generate_tpch.json         TPC-H generation and row-count checks, one task per entity
  tpch/                      subproject "tpch"
    tpch_medallion.json        TPC-H bronze then silver, one pair of tasks per entity
dags/
  lakehouse.py             The platform stub: the only file allowed in dags/
notebooks/
  common/                  Shared helpers for Airflow runs and Jupyter:
    config_loader.py         load and validate configs/<env>.yml (and configs/<product>/<env>.yml)
    cli.py                   --environment, --config-dir, task arguments (parse_task_args)
    job_runtime.py           start_spark_job(): config, then the platform's Spark session
    jupyter_environment_resolver.py   Jupyter start-up: the clone, the environment, spark and config (%run)
  workload/                Spark jobs (Jupytext py:percent files, also notebooks), per subproject
    sample/                  subproject "sample" (the entry points of workflows/sample/)
      other/                   notebooks that fit no medallion layer
        test_environment.py      creates the smoke table
        count_sample_rows.py     counts its rows
        generate_tpch.py         generates TPC-H data with DuckDB and checks one entity's row count
    tpch/                    subproject "tpch" (the entry points of workflows/tpch/)
      bronze/bronze_ingestion.py    appends one generated TPC-H entity to its bronze table
      silver/silver_processing.py   streams bronze changes and merges them into the silver table
configs/                   Non-secret settings: dev.yml, uat.yml, prod.yml, optional <product>/<env>.yml
tests/                     pytest and Hypothesis tests for the helpers and workloads
scripts/code_quality.sh    lint, flake8, bandit (used by CI)
Jenkinsfile                CI checks (no deployment)
requirements.txt           Extra Python packages for the workload code (duckdb), on top of the platform's set
requirements-dev.txt       Test and lint tools
AGENTS.md                  Rules for coding agents working here, including the subproject layout
```

**Subprojects**: workflows and their notebooks are grouped by subproject, with the same folder name under `workflows/` and `notebooks/workload/` (here `sample` and `tpch`). A workflow in `workflows/<project>/` runs entry points from `notebooks/workload/<project>/`.

**Layers inside a subproject's notebooks** (workflows have none): `notebooks/workload/<project>/` may hold the medallion layer folders `bronze/` (raw ingestion), `silver/` (cleaned or conformed data), `gold/` (curated, consumption-ready data), plus `ops/` (operational notebooks run as needed: migrations, data patches, maintenance), `deploy/` (deployment of assets the pipelines don't create, such as views) and `other/` (notebooks that fit no medallion layer; `sample`'s three notebooks live there). A workflow names a layer notebook as `"entrypoint": "bronze/load_orders.py"` or `"other/generate_tpch.py"`. Only these six folders, one level deep:

```text
notebooks/workload/<project>/
  bronze/      silver/      gold/      ops/      deploy/      other/
```
 DAG IDs don't include the subproject (`default-uat-generate_tpch`), so workflow names are unique across the repository. Shared code stays in `notebooks/common/`. To add a subproject, create both folders; see [AGENTS.md](AGENTS.md).

## Workflow JSON reference

One file per DAG: `workflows/<project>/<name>.json`. A complete example:

```json
{
  "apiVersion": "lakehouse.local/workflow/v1",
  "name": "daily_sales",
  "description": "Load yesterday's sales, then refresh the summary.",
  "schedule": "0 3 * * *",
  "tags": ["sales"],
  "tasks": [
    {
      "name": "load_sales",
      "entrypoint": "load_sales.py",
      "args": ["--source", "sales_raw", "--days", "1"],
      "retries": 2,
      "retry_delay_seconds": 300,
      "execution_timeout_seconds": 3600
    },
    {"name": "refresh_summary", "entrypoint": "refresh_summary.py", "runs_after": ["load_sales"]}
  ]
}
```

**Workflow fields**

| Field | Required | Type and limits | Meaning |
|---|---|---|---|
| `apiVersion` | yes | exactly `lakehouse.local/workflow/v1` | The contract version |
| `name` | yes | 1–100 of `a-z A-Z 0-9 _ . -`, not starting with `.`; must equal the file name | DAG name; the DAG ID is `<bundle>-<name>` |
| `schedule` | yes | `null`, or a cron expression or preset (`@daily`), at most 100 characters | `null` means manual runs only |
| `description` | no | printable text, at most 500 characters | Shown in Airflow; a default names the tasks |
| `tags` | no | at most 10 distinct tags of `a-z A-Z 0-9 _ . : -` (1–50 characters) | Extra Airflow tags; the bundle name and `spark` are always added, and `spark` may not be listed |
| `tasks` | yes | 1–50 tasks | See below |

**Task fields**

| Field | Required | Type and limits | Meaning |
|---|---|---|---|
| `name` | yes | as workflow `name`; unique in the workflow | Task ID `submit_<name>` |
| `entrypoint` | yes | a `.py` file name that exists in `notebooks/workload/<project>/`, or `<layer>/<file>.py` for a notebook in a layer folder (`bronze`, `silver`, `gold`, `ops`, `deploy`, `other`) | The job to run; one file may serve several tasks |
| `runs_after` | no | list of other task names in this workflow, default `[]` | Wait for these tasks; no task may wait for itself, and the order may not loop |
| `args` | no | list of at most 50 strings (each 1–500 printable characters), default `[]` | Passed to the entry point after `--` (see [entry points](#writing-an-entry-point)) |
| `retries` | no | integer 0–10 | Airflow retries for this task |
| `retry_delay_seconds` | no | integer 0–3600; only with `retries` ≥ 1 | Wait between retries |
| `execution_timeout_seconds` | no | integer 1–86400 | Fail the task if it runs longer |

- **Strict checking**: any unknown field, wrong type, or out-of-range value is an error. For example, `true` isn't accepted as a number, and `"command"` isn't a field.
- **One bad file stops the whole bundle**: if any file in `workflows/` is invalid, Airflow shows a single import error for `dags/lakehouse.py` that lists every problem by file and field. None of that bundle's DAGs load until it's fixed, so CI checks the files before they're merged.
- **No templates**: `args` are passed exactly as written. Airflow templates such as `{{ ds }}` aren't rendered, because a template could read Airflow's connections and variables. A scheduled job that needs a date should work it out itself, for example yesterday in UTC.

## The DAG stub

`dags/lakehouse.py` must contain exactly this:

```python
# Airflow DAGs for this repository, built by the lakehouse platform from workflows/*.json.
from lakehouse_dags import load_workflows

load_workflows(globals(), __file__)
```

- **Never edit the stub, and don't add other files to `dags/`**. CI refuses both. Declare DAGs in `workflows/` instead.
- **The comment matters**: Airflow only parses files that mention both "airflow" and "DAG".
- **No workflows**: a repository without `workflows/` simply has no DAGs.

## Writing an entry point

An entry point is a Python file in `notebooks/workload/<project>/` or one of its layer folders. In Airflow it's started as:

```text
spark-submit --master local[*] /opt/lakehouse-bundle/notebooks/workload/<project>/<entrypoint> \
    --environment <prod|uat> --config-dir /opt/lakehouse-bundle/configs [-- <args…>]
```

Use the shared helpers rather than parsing `sys.argv` yourself:

```python
from notebooks.common.cli import parse_task_args
from notebooks.common.job_runtime import start_spark_job

TASK_ARGS_DEFINITION = {"date": {"required": True}, "mode": {"default": "append"}}

spark, config = start_spark_job("load_sales")  # reads --environment and --config-dir; dev in Jupyter
arguments = parse_task_args(TASK_ARGS_DEFINITION)     # {"date": "2026-11-10", "mode": "append"}
```

- **Who does what**: the platform starts the Spark session (the Polaris catalogs, your run's or your own token, redaction) with its `lakehouse_spark` module, which both platform images provide. This repository keeps its configuration: every key of `configs/<env>.yml` reaches the job.
- **`start_spark_job(app_name)`**:
  - parses `--environment` and `--config-dir`, or in Jupyter uses `LAKEHOUSE_ENVIRONMENT` (default `dev`);
  - loads the config (in Airflow, preferring the product folder; see below);
  - asks the platform for the session with the config's `catalog_name`, and returns `(spark, config)`. The Spark application is `<env>-<app_name>`.
- **Task arguments**: declare them once and read them with `parse_task_args(declaration)`:
  - **declaration**: each name maps to `{"required": True}`, `{"default": "<text>"}` or `{}`; `date` is the option `--date`, `scale_factor` is `--scale-factor`;
  - **sources**: the workflow task's `args` (after `--`) in Airflow; in Jupyter only the notebook's [`TASK_ARGS_VALUES` dict](#working-in-jupyter). Airflow never reads `TASK_ARGS_VALUES`: without `args`, a run gets the declared defaults;
  - **values are strings**, never converted or checked: check them in the job (as `generate_tpch.py` does);
  - **structural errors** (an unknown option, a missing required one, an option given twice or without a value) are reported together with the usage: the task exits with status 2 in Airflow, and the cell raises `TaskArgumentError` in Jupyter.

  `cli.task_args()` still returns the raw list after `--` (empty in Jupyter). Arguments are passed as a list and never go through a shell.
- **Environment variables** set in the Airflow container: `LAKEHOUSE_ENVIRONMENT` (`prod` or `uat`), `LAKEHOUSE_PRODUCT` (for example `default`), and `PYTHONPATH=/opt/lakehouse-bundle`, so `notebooks.common` imports work.
- **The same structure in every notebook**, as `## ` markdown sections:
  1. the title (`# `) and what the job does;
  2. **Initialization**: the two Jupyter cells below;
  3. **Imports**: imports and logging;
  4. the job's own sections (for example **Task arguments**, **TPC-H rules**, **Generate and count**): settings and functions, no top-level work;
  5. **Execution**: only the `if __name__ == "__main__":` block that runs the job.

  CI checks this order.
- **Start every notebook with the Initialization section** (see [Working in Jupyter](#working-in-jupyter)): `# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp` and `# %run ../../../common/jupyter_environment_resolver.py` (from a layer folder), right after the title cell. CI checks that every file in `notebooks/workload/` has it.
- **Stop Spark at the end**: call `spark.stop()` in a `finally:` block. Put the run code under `if __name__ == "__main__":` so tests and notebooks can import the file without starting Spark.
- **Packages**: entry points run on the platform's Python 3.10 environment plus this repository's `requirements.txt`; see [Python packages](#python-packages).

## Python packages

Workload code runs on one Python environment, the same in Airflow's Spark containers and in the Jupyter kernel: **Python 3.10** with the platform's pinned packages, and PySpark 3.5.5 from the Spark installation.

- **The platform's packages**: PyYAML, requests, pandas, numpy, pyarrow, ipykernel, jupytext and ipywidgets, with their dependencies, at versions fixed by the platform's lock (`infra/workload-python/requirements.lock` in the platform repository). Other packages are not available unless this repository asks for them.
- **This repository's extras**: list them in `requirements.txt` at the repository root, one plain requirement per line, for example:

  ```text
  duckdb==1.5.6  # generate_tpch.py: TPC-H data generation
  ```

  - **Pin them** (`==`), so every run gets the same version.
  - **The platform's versions win**: the lock is always applied as a constraint. A requirement that needs a different version of a locked package (for example `pandas==2.2.2`, or `numpy>=2`) fails, in CI and in the run. Listing a locked package at its locked version is allowed and changes nothing.
  - **Allowed lines**: package names with optional extras (`requests[socks]`), version specifiers (`==`, `>=`, `<`, `~=`, ...), environment markers, and comments.
  - **Refused lines**: pip options (`-r`, `-e`, `-c`, `--index-url`, `--extra-index-url`, `--hash`, ...), URLs, paths and `name @ url` references, and `pyspark`, `py4j`, `pip`, `setuptools`, `wheel` (the platform provides them).
  - **Prebuilt wheels only**: every package, dependencies included, needs a wheel for CPython 3.10 on Linux **aarch64** with glibc 2.31 or older (`manylinux_2_17` to `manylinux_2_31`, or `manylinux2014`). Nothing is compiled. For example, `pytpch` 0.2.0 ships only an x86_64 wheel for glibc 2.34, so it can't be used here; DuckDB's built-in TPC-H generator replaces it.
- **When they are installed**:
  - **Airflow**: by `install_requirements` at the start of every run, into that run's container only, from public PyPI. A run of a repository without `requirements.txt` needs no network for this. With extras, the install time is part of the run (a few seconds for `duckdb`).
  - **Jupyter**: when you run `lakehouse-install-requirements` (see [Working in Jupyter](#working-in-jupyter)).
  - **CI**: `lakehouse-validate-workflows` checks the file against the lock for the platform's architecture, and the test stage installs it so the unit tests can use it.
- **DuckDB's TPC-H extension**: `generate_tpch.py` uses DuckDB's `tpch` extension, which DuckDB downloads from `extensions.duckdb.org` the first time it is used in a container (each run, and once per Jupyter home).

## Configs and environments

| Environment | Used by | File |
|---|---|---|
| `prod` | Airflow, bundle `<product>-main` | `configs/<product>/prod.yml`, else `configs/prod.yml` |
| `uat` | Airflow, bundle `<product>-uat` | `configs/<product>/uat.yml`, else `configs/uat.yml` |
| `dev` | Jupyter only | `configs/dev.yml` |

- **Required keys**: `storage_path` (for example `s3a://bucket-default/`, ending with `/`) and `database_name`, the product's namespace for that environment, for example `default_lh`, `default_lhuat` or `default_lhdev`.
  - **Usually present**: `catalog_name` (`lakehouse`, `lakehouse_uat` or `lakehouse_dev`).
  - **For streaming jobs**: `checkpoint_path`, `s3ckpt://<bucket>/checkpoints` in the environment's own bucket (`bucket-default-dev`, `bucket-default-uat`, `bucket-default`). `s3ckpt://` is the platform's checkpoint filesystem; the platform mounts the key for it (Airflow: the run's environment; Jupyter: `dev`, for the product's owners and developers). Give each stream its own subpath, `<checkpoint_path>/<project>/<target_table>`.
  - **Other keys**: any other keys, including nested ones, are passed through to the job as read-only values.
- **Strict loading**: the loader refuses unknown environment names and never falls back from one environment to another. A missing file fails `validate_environment` before any task runs.
- **One repository, several products**: put each product's settings in `configs/<product>/`; Airflow uses them (the platform sets the product from the bundle). The `configs/<env>.yml` files are the fallback, and the only files Jupyter reads.
- **Your own settings**: add any keys you need, for example a source dataset that differs between `dev`, `uat` and `prod`; jobs read them from `config`.
- **The values must match the platform**: they have to be the product's namespaces and buckets from the platform's data product file. Access to anything else is refused by Polaris.
- **No secrets**: never put credentials, tokens or endpoints in configs.

## Working in Jupyter

1. Sign in to JupyterHub (<http://jupyterhub.localhost:8000>) with your platform account. You need to be a developer or analyst of the product.
2. Clone this repository into your workspace and open a file from `notebooks/workload/<project>/` (for example `notebooks/workload/sample/other/`) as a notebook. Jupytext reads the `py:percent` format.
3. Run the **Initialization** section at the top of the notebook. Every notebook starts with it:

   ```python
   # %%
   # !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp

   # %%
   # %run ../../../common/jupyter_environment_resolver.py
   ```

   In the `.py` file both lines are comments (Jupytext's convention), so `spark-submit` in Airflow skips them; opened in Jupyter they become a shell command and a `%run`.
   - The first cell installs this repository's `requirements.txt` extras. **After the first install in a server session, restart the kernel** and run all cells; later runs print `Nothing to add`.
   - The second cell finds the clone that holds the notebook, selects `dev`, and starts Spark with **your own** identity, so you see and write only what your groups allow (for a developer, read in `prod` and `uat`, write in `dev`). It defines `spark` and `config`.
4. Run the rest of the notebook.

The path `~/work/opensource-lakehouse-sample-dp` assumes the clone is in `~/work`, as in step 2; adjust it if you cloned elsewhere.

**Another environment**: run `%env LAKEHOUSE_ENVIRONMENT=uat` (or `prod`) before the Initialization section. A kernel that already has a session needs a restart to switch.

**Task arguments in Jupyter**: set them in the notebook's `TASK_ARGS_VALUES` dict, under the Task arguments section, next to the declaration, then run the job's cells:

```python
# The arguments this job accepts, in Airflow and in Jupyter
TASK_ARGS_DEFINITION = {"entity": {"required": True}, "scale_factor": {"default": "0.01"}}

# Jupyter only: this run's values (Airflow uses the workflow's args)
TASK_ARGS_VALUES = {"entity": "orders", "scale_factor": "0.1"}
```

Values are strings, as Airflow passes them; a name left out takes its default. A name that isn't declared, a non-string value, or a missing required argument raises `TaskArgumentError` with the usage line. Only Jupyter reads `TASK_ARGS_VALUES`, so the committed example never affects an Airflow run.

**The kernel**: the only kernel is **Lakehouse (Python 3.10)**, with the same packages as Airflow runs. Notebooks saved with an older kernel open with it.

**This repository's extras** (`requirements.txt`): the Initialization section installs them; you can also run the command in a JupyterLab terminal, then restart the kernel:

```bash
cd ~/work/opensource-lakehouse-sample-dp        # your clone
lakehouse-install-requirements        # or: lakehouse-install-requirements path/to/clone
```

The packages go to `~/.local/lakehouse/python3.10`, which lasts only for the current server session (only `~/work` is kept across restarts): **rerun the command after every server start**. Running the command for another repository adds its packages too. When the platform's lock changes, the command asks you to rerun it with `--reset`, which empties that folder first.

**TPC-H in a notebook**: open `notebooks/workload/sample/other/generate_tpch.py`, set the entity in `TASK_ARGS_VALUES` (for example `"orders"`; the committed example is `"region"`), and run all cells.

`workflows/` and `dags/` play no part in Jupyter. An entry point that works in Jupyter with `dev` should behave the same in Airflow with `uat` and `prod`, apart from data and permissions.

## CI in Jenkins

The platform creates a folder named after the product in Jenkins (<http://127.0.0.1:8090>), with two multibranch jobs running this `Jenkinsfile`:

| Job | Builds | Checks for changes |
|---|---|---|
| `<product>_ci` | `main` and `uat` | every 5 minutes |
| `<product>_cd` | every branch of this repository with an open pull request (not forks) | every 30 minutes |

The pipeline stages are:
1. install the test dependencies, and `requirements.txt` constrained by the platform's lock;
2. compile `dags` and `notebooks`;
3. **validate workflows** (`lakehouse-validate-workflows .`): the platform's own rules for `workflows/*.json`, the exact stub, and nothing else in `dags/`, then `requirements.txt` against the platform's lock (it lists the packages it would add);
4. Ruff and Black, Flake8, and Bandit, in parallel;
5. pytest.

CI doesn't deploy anything: Airflow picks up merged changes from Git by itself.

## The tpch subproject

TPC-H data through a bronze and a silver layer, in the environment's namespace:

| Layer | Notebook | Table | What it does |
|---|---|---|---|
| bronze | `bronze/bronze_ingestion.py` | `tpch_<entity>_db_brz` | Generates one entity with DuckDB at `--scale-factor` (default 0.01) and appends it, with `scale_factor` and `bronze_ingestion_timestamp`; append-only |
| silver | `silver/silver_processing.py` | `tpch_<entity>` | Streams the bronze snapshots added since the last run (checkpoint `<checkpoint_path>/tpch/tpch_<entity>`) and merges the newest row per key (`MERGE_KEYS`); a row is only replaced by a newer one |

- **Workflow** `tpch_medallion` (manual): per entity, `tpch_<entity>_db_brz_load`, then `tpch_<entity>_load`, in two lanes: bronze tasks one after another, and each silver task after its bronze task and the previous silver task. A run's tasks share one Spark container, so at most two Spark jobs run at once (eight at once ran out of memory). Each task retries once after 60 s. Each run adds a bronze batch and merges it.
- **Tables** are created by the first run at `<storage_path>/<catalog_name>/<database_name>/<table>`. The product's writer can't drop tables; ask an owner or the platform team.
- **Conventions**: notebooks `<layer>_<action>.py`; bronze tables `<project>_<entity>_<source>_brz`; silver tables `<project>_<entity>`; workflows `<project>_<purpose>`; tasks `<target_table>_load`; checkpoints `<checkpoint_path>/<project>/<target_table>` (see [AGENTS.md](AGENTS.md)).
- **Reprocess silver** (`silver_lookback_days`, default 0): with N > 0, silver deletes the entity's checkpoint and merges the bronze snapshots of the last N days again (safe: rows never get older).
  - **In Jupyter** (`dev`): set `"silver_lookback_days": "<N>"` in the notebook's `TASK_ARGS_VALUES`.
  - **In uat or prod**: trigger `<bundle>-tpch_medallion` with the platform's `task_args`, giving each silver task to reprocess its lookback, for example `{"tpch_region_load": {"silver_lookback_days": "7"}, "tpch_orders_load": {"silver_lookback_days": "7"}}`. The value is added as `--silver-lookback-days=7` for that run only; scheduled runs and the other tasks are unchanged, and the workflow file is never edited.
- **Limits**: bronze is append-only; a bronze snapshot that deletes or overwrites rows stops the silver stream. Each checkpoint must have one writer at a time, so don't run the same entity's silver from Jupyter and Airflow at once.

## How-to

**Add a workflow**
1. Write the job in `notebooks/workload/<project>/<layer>/<job>.py`, in the layer folder that matches its role (see [entry points](#writing-an-entry-point)), and try it in Jupyter with `dev`. In a layer folder, the Initialization's `%run` path is `../../../common/jupyter_environment_resolver.py`.
2. Add `workflows/<project>/<name>.json` with `apiVersion`, `name` (unique in the repository), `schedule` and `tasks`.
3. Open a pull request into `uat`. `<product>_cd` validates and tests the branch.
4. Merge. Within about 5 minutes Airflow shows `<product>-uat-<name>`; run it there.
5. Open a pull request from `uat` into `main`. After the merge, `<product>-main-<name>` appears.

**Add a task with arguments and retries**: add an entry to `tasks` with `args`, `retries` and, optionally, `retry_delay_seconds`. Declare them in the entry point and read them with `parse_task_args(...)`.

**Add a Python package**:
1. Add `<package>==<version>` to `requirements.txt`, and check that the package has a Linux aarch64 wheel for CPython 3.10 (on PyPI, the file list of that version).
2. In Jupyter, run `lakehouse-install-requirements`, restart the kernel, and try your code with `dev`.
3. Open a pull request. CI refuses the change if the package conflicts with the platform's versions or has no suitable wheel.
4. If the package belongs in every product's environment, ask the platform team to add it to the platform's set instead.

**Run a dependency**: list the earlier task's name in `runs_after`. Tasks with no dependencies start in parallel after the config check.

**Check locally before pushing**:

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m compileall -q dags notebooks
PATH=".venv/bin:$PATH" scripts/code_quality.sh all
.venv/bin/python -m pytest -q
```

The workflow validator runs in Jenkins. With a copy of the platform's `lakehouse_dags` package, you can also run it yourself: `PYTHONPATH=<platform>/infra/airflow python3 -m lakehouse_dags.validate .`

**Remove a workflow**: delete its JSON file. After the next bundle refresh the DAG disappears from Airflow, and its run history stays in Airflow's records.

## Limits

- **No Python DAGs**: DAGs are declared only in JSON, and CI refuses Python files in `dags/` other than the stub. Until the platform enforces this in Airflow too, such files would still be parsed there, so keep `dags/` clean.
- **One container per run**: Spark runs in `local[*]` mode inside one container per DAG run, not on a distributed cluster.
- **Fixed environments**: Airflow runs only `prod` (from the production branch) and `uat` (from the UAT branch). `dev` is for Jupyter, and feature branches are tested in CI, not in Airflow.
- **Public repository only**: the platform reads it anonymously.
- **Scans, not webhooks**: Jenkins checks for changes every 5 or 30 minutes, and Airflow refreshes bundles about every 5 minutes. Pull requests from forks aren't built.
- **Packages from public PyPI, prebuilt aarch64 wheels only**: no private index, no source builds, and no cache: each Airflow run with a `requirements.txt` installs it again.
- **The platform's versions are fixed for a repository**: to change a locked package's version, the platform's lock has to change.
