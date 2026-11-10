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
7. [Configs and environments](#configs-and-environments)
8. [Working in Jupyter](#working-in-jupyter)
9. [CI in Jenkins](#ci-in-jenkins)
10. [How-to](#how-to)
11. [Limits](#limits)

## What lives where

| This repository | The lakehouse platform |
|---|---|
| `workflows/*.json`: which DAGs exist, their tasks, order, schedule, arguments, retries and timeouts | Turning each workflow into an Airflow DAG (the `lakehouse_dags` factory) |
| `notebooks/workload/*.py`: the Spark jobs, also usable as notebooks | Starting one Spark container per DAG run, with this repository mounted read-only |
| `notebooks/common/`: config loading, argument parsing, Spark session start-up | Issuing the product's short-lived write token to each run, through the token broker |
| `configs/`: non-secret settings per environment (storage path, catalog, database) | The Git bundles that Airflow reads from this repository (`<product>-main`, `<product>-uat`) |
| `dags/lakehouse.py`: a fixed two-line stub | The Jenkins jobs that check this repository, and the workflow validator they use |

Nothing in this repository holds a password, key, or token, and nothing should.

## How a run works

1. **Bundles**: the platform's data product file names this repository in its `repo` block. Airflow then keeps two Git bundles of it:
   - `<product>-main` tracks the production branch (`main` for `default`) and runs in environment `prod`;
   - `<product>-uat` tracks the UAT branch (`uat`) and runs in environment `uat`.

   Each bundle checks out `dags/`, `workflows/`, `notebooks/` and `configs/`, and refreshes about every 5 minutes.
2. **DAGs**: Airflow parses `dags/lakehouse.py`, which asks the platform to build one DAG per `workflows/<name>.json`. The DAG ID is `<bundle>-<name>`, for example `default-uat-test_environment`. The platform's token broker relies on that prefix to pick the product's writer, so DAG IDs are never chosen in this repository.
3. **Each DAG has the same fixed shape**:

   ```text
   create_cluster ─▶ validate_environment ─▶ submit_<task> … (in runs_after order) ─▶ stop_cluster ─▶ verify_workloads_succeeded
   ```

   - `create_cluster` registers the run with the token broker and starts one Spark container. The container mounts the run's exact bundle commit at `/opt/lakehouse-bundle`, read-only.
   - `validate_environment` loads the environment's config inside that container with this repository's own `notebooks/common/config_loader.py`.
   - Each `submit_<task>` runs one entry point with `spark-submit --master local[*]` as its own Spark application. Tasks without `runs_after` start together; the others wait for their predecessors.
   - `stop_cluster` always runs, even after failures. It removes the container and revokes the run's token.
   - `verify_workloads_succeeded` succeeds only if every task succeeded.
4. **Credentials**: the container gets only a short-lived token for the product's writer user and a way to renew it during the run. Spark reads and writes Iceberg tables through the Polaris catalog, and the storage credentials come from Polaris. Everything a run does is within the product's own namespaces and buckets.
5. **Versions**: code, configs and workflows always come from the same commit, the one recorded for that run.

## Repository layout

```text
workflows/                 One JSON file per Airflow DAG (see the reference below)
  test_environment.json
dags/
  lakehouse.py             The platform stub: the only file allowed in dags/
notebooks/
  common/                  Shared helpers for Airflow runs and Jupyter:
    config_loader.py         load and validate configs/<env>.yml (and configs/<product>/<env>.yml)
    cli.py                   --environment, --config-dir, and task arguments after --
    job_runtime.py           start_spark_job(): config plus a catalog-ready Spark session
  workload/                Spark jobs (Jupytext py:percent files, also notebooks)
    test_environment.py      creates the smoke table
    count_sample_rows.py     counts its rows
    jupyter_helper.py        Jupyter start-up (dev settings)
configs/                   Non-secret settings: dev.yml, uat.yml, prod.yml, optional <product>/<env>.yml
tests/                     pytest and Hypothesis tests for the helpers and workloads
scripts/code_quality.sh    lint, flake8, bandit (used by CI)
Jenkinsfile                CI checks (no deployment)
requirements-dev.txt       Test and lint tools
AGENTS.md                  Rules for coding agents working here
```

## Workflow JSON reference

One file per DAG: `workflows/<name>.json`. A complete example:

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
| `entrypoint` | yes | a `.py` file name that exists in `notebooks/workload/` (no folders) | The job to run; one file may serve several tasks |
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

An entry point is a Python file in `notebooks/workload/`. In Airflow it's started as:

```text
spark-submit --master local[*] /opt/lakehouse-bundle/notebooks/workload/<entrypoint> \
    --environment <prod|uat> --config-dir /opt/lakehouse-bundle/configs [-- <args…>]
```

Use the shared helpers rather than parsing `sys.argv` yourself:

```python
from notebooks.common.cli import task_args
from notebooks.common.job_runtime import start_spark_job

spark, config = start_spark_job("load_sales")  # reads --environment and --config-dir; dev in Jupyter
extra = task_args()                             # the workflow task's "args"; [] in Jupyter
```

- **`start_spark_job(app_name)`**:
  - parses `--environment` and `--config-dir`, or in Jupyter uses `LAKEHOUSE_ENVIRONMENT` (default `dev`);
  - loads the config, preferring the product folder (see below);
  - returns `(spark, config)` with the Iceberg catalogs and token handling configured.
- **Arguments**: `cli.parse_args()` returns the same values plus `task_args`, and `cli.task_args()` returns only the arguments after the first `--`, unchanged. Arguments are passed as a list and never go through a shell.
- **Environment variables** set in the Airflow container: `LAKEHOUSE_ENVIRONMENT` (`prod` or `uat`), `LAKEHOUSE_PRODUCT` (for example `default`), and `PYTHONPATH=/opt/lakehouse-bundle`, so `notebooks.common` imports work.
- **Stop Spark at the end**: call `spark.stop()` in a `finally:` block. Put the run code under `if __name__ == "__main__":` so tests and notebooks can import the file without starting Spark.
- **Packages**: entry points run on the platform's Spark runtime image (Spark 3.5.5, Iceberg 1.10.2, Python 3.10, with PyYAML, pandas, numpy and pyarrow), and nothing else is installed. A shared requirements file for Airflow and Jupyter is planned by the platform.

## Configs and environments

| Environment | Used by | File |
|---|---|---|
| `prod` | Airflow, bundle `<product>-main` | `configs/<product>/prod.yml`, else `configs/prod.yml` |
| `uat` | Airflow, bundle `<product>-uat` | `configs/<product>/uat.yml`, else `configs/uat.yml` |
| `dev` | Jupyter only | `configs/<product>/dev.yml`, else `configs/dev.yml` |

- **Required keys**: `storage_path` (for example `s3a://bucket-default/`, ending with `/`) and `database_name`, the product's namespace for that environment, for example `default_lh`, `default_lhuat` or `default_lhdev`.
  - **Usually present**: `catalog_name` (`lakehouse`, `lakehouse_uat` or `lakehouse_dev`).
  - **Other keys**: any other keys, including nested ones, are passed through to the job as read-only values.
- **Strict loading**: the loader refuses unknown environment names and never falls back from one environment to another. A missing file fails `validate_environment` before any task runs.
- **One repository, several products**: put each product's settings in `configs/<product>/`. The `configs/<env>.yml` files are the fallback.
- **The values must match the platform**: they have to be the product's namespaces and buckets from the platform's data product file. Access to anything else is refused by Polaris.
- **No secrets**: never put credentials, tokens or endpoints in configs.

## Working in Jupyter

1. Sign in to JupyterHub (<http://jupyterhub.localhost:8000>) with your platform account. You need to be a developer or analyst of the product.
2. Clone this repository into your workspace and open a file from `notebooks/workload/` as a notebook. Jupytext reads the `py:percent` format.
3. Run the cells. `# %run ./jupyter_helper.py` finds the repository root, selects `dev`, and starts Spark with **your own** identity, so you see and write only what your groups allow (for a developer, read in `prod` and `uat`, write in `dev`).

`workflows/` and `dags/` play no part in Jupyter. An entry point that works in Jupyter with `dev` should behave the same in Airflow with `uat` and `prod`, apart from data and permissions.

## CI in Jenkins

The platform creates a folder named after the product in Jenkins (<http://127.0.0.1:8090>), with two multibranch jobs running this `Jenkinsfile`:

| Job | Builds | Checks for changes |
|---|---|---|
| `<product>_ci` | `main` and `uat` | every 5 minutes |
| `<product>_cd` | every branch of this repository with an open pull request (not forks) | every 30 minutes |

The pipeline stages are:
1. install the test dependencies;
2. compile `dags` and `notebooks`;
3. **validate workflows** (`lakehouse-validate-workflows .`): the platform's own rules for `workflows/*.json`, the exact stub, and nothing else in `dags/`;
4. Ruff and Black, Flake8, and Bandit, in parallel;
5. pytest.

CI doesn't deploy anything: Airflow picks up merged changes from Git by itself.

## How-to

**Add a workflow**
1. Write the job in `notebooks/workload/<job>.py` (see [entry points](#writing-an-entry-point)) and try it in Jupyter with `dev`.
2. Add `workflows/<name>.json` with `apiVersion`, `name`, `schedule` and `tasks`.
3. Open a pull request into `uat`. `<product>_cd` validates and tests the branch.
4. Merge. Within about 5 minutes Airflow shows `<product>-uat-<name>`; run it there.
5. Open a pull request from `uat` into `main`. After the merge, `<product>-main-<name>` appears.

**Add a task with arguments and retries**: add an entry to `tasks` with `args`, `retries` and, optionally, `retry_delay_seconds`. Read the arguments with `task_args()`.

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
- **Fixed packages**: entry points can use only the packages in the platform's Spark image.
