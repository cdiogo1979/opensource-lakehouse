# Functional Design — Workload Foundation (shared helpers)

The shared helpers in `notebooks/common/`, used by every subproject in Airflow runs and in Jupyter. Architecture: [`../application-design.md`](../application-design.md). Replaces the retired Nessie/DockerOperator design.

## `config_loader.py`
- `load_environment_config(environment, config_dir=None, product=None)` → `EnvironmentConfig` (a read-only mapping; `.environment`, `.to_dict()`).
- Accepts only `dev`, `uat`, `prod` (`SUPPORTED_ENVIRONMENTS`); requires `storage_path` and `database_name` (`REQUIRED_KEYS`); every other key, nested ones included, passes through. With a product (`^[a-z][a-z0-9]{1,19}$`), `configs/<product>/<env>.yml` is read before `configs/<env>.yml` (Airflow only). Never falls back across environments; refuses missing files, malformed YAML, non-mapping roots and invalid required values.

## `cli.py`
- `parse_args(argv)`: `--environment` and `--config-dir`, before `--`.
- `parse_task_args(declaration, argv=None, prog=None)`: the job's declared arguments as strings; each name (`[a-z][a-z0-9_]{0,49}`) maps to `{"required": True}`, `{"default": "<text>"}` or `{}`; `scale_factor` is `--scale-factor`. Values come from the command line after `--` (Airflow; without `args`, the declared defaults), or in Jupyter only from the notebook's `TASK_ARGS_VALUES` dict (argument name to string value; an undeclared name, a non-string value or a non-dict is a problem). Airflow never reads `TASK_ARGS_VALUES`. Structural problems are reported together with the usage: exit 2 in Airflow, `TaskArgumentError` in Jupyter. Values are never converted or checked: the notebook checks them.
- `task_args(argv)`: the raw list after `--`; `[]` in Jupyter (never the kernel's command line).

## `job_runtime.py`
- `start_spark_job(app_name, argv=None)` → `(spark, config)`: in Airflow it parses `--environment` and `--config-dir`, uses `LAKEHOUSE_PRODUCT`, loads the config and calls the platform's `lakehouse_spark.create_spark_session("<env>-<app_name>", config["catalog_name"])`; in Jupyter it uses `jupyter_environment()` (`LAKEHOUSE_ENVIRONMENT`, default `dev`). A config without `catalog_name` is refused.

## Jupyter scripts (`%run`)
- `jupyter_environment_resolver.py`: finds the clone that holds the notebook (`notebooks/common/job_runtime.py` marker), names the application `<env>-<notebook>`, and defines `spark` and `config` in the notebook.

## Sample workloads (`notebooks/workload/sample/other/`)
`test_environment.py` (creates the smoke table twice), `count_sample_rows.py` (counts it), `generate_tpch.py` (DuckDB TPC-H generation with row-count checks); workflows `workflows/sample/test_environment.json` and `generate_tpch.json`.

## Failure behavior
Config, argument, import, catalog or storage failures fail the task with the message in the (redacted) task log; in Jupyter they raise in the cell. Nothing falls back to another environment or identity.

## Verification
`tests/workload_foundation/` (config loader, CLI, task arguments, job runtime, Jupyter scripts, notebook structure, product bundles, properties). Latest: 2026-11-11, 112 passed with the `tpch` suite (2 DuckDB skips locally; DuckDB tests pass in the Spark runtime image and in Jenkins).
