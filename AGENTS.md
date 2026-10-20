# Project guide for agents

## Purpose and layout

This repository contains environment-configured Python Spark workloads and Airflow DAGs. Airflow submits workloads to an externally managed Spark service. A shared Airflow 3 deployment reads versioned Git DAG Bundles; Jenkins validates and gates repository changes but does not publish artifacts.

- `configs/`: One non-secret YAML file per environment: `dev.yml`, `uat.yml`, and `prod.yml`. Each defines `storage_path` and `database_name`.
- `notebooks/common/`: Shared config loader, standard workload CLI parser, and Spark job bootstrap for Jupyter and `spark-submit`.
- `notebooks/workload/`: Exported Python Spark jobs and Jupytext-compatible Jupyter helper scripts. Keep environment values in YAML.
- `dags/`: Thin DAG declarations, `dag_factory.py` for standard validation and Docker Spark tasks, and `dag_defaults.py` for shared DAG settings and bundle-name environment selection.
- `airflow_bundle_config.example.json`: Secret-free example `dag_bundle_config_list` with a dev branch placeholder plus fixed UAT and production refs.
- `airflow_bundle_client.py`: Operator CLI that changes only `lakehouse-dev.tracking_ref` in the deployment-managed bundle config. Its apply command is deployment-specific and supplied externally.
- `airflow_bundle_client.example.yml`: Example non-secret client settings. Never add credentials.
- `AIRFLOW_BUNDLES.md`: Airflow bundle and dev branch-selection setup and usage.
- `tests/`: pytest and Hypothesis coverage for workload configuration and deployment-client behavior.
- `Jenkinsfile`: Repository CI checks only. It does not push files to Airflow or change bundle refs.
- `aidlc-docs/current/`: Active AI-DLC intent artifacts, state, and audit log. Follow `.agents/skills/aidlc-workflows/SKILL.md` for workflow work.

## Git DAG Bundle contract

- Configure one Airflow 3 deployment with three unique Git bundles: `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod`.
- The dev bundle tracks an operator-selected feature branch. UAT tracks `uat`; production tracks `main`.
- Each bundle checks out the same `dags/`, `configs/`, and `notebooks/` directories from its selected Git ref, preserving repository root as the bundle root.
- The dev bundle follows a selected feature branch; UAT follows `uat`; production follows `main`. Each bundle checks out the same `dags/`, `configs/`, and `notebooks/` paths from its selected branch, so code and config are versioned together.
- Keep Git bundle versioning enabled. Each run must use its recorded bundle commit for the DAG, config, helpers, and Spark application.
- Store Git credentials in an Airflow Git connection or approved secrets backend. Never embed credentials in the repository URL, bundle config, example settings, DAGs, or logs.
- Airflow's native UI does not edit `tracking_ref`. Use the operator CLI and the deployment-provided apply/reload command. Confirm Airflow has fetched and parsed the selected branch before testing; client apply success alone does not prove readiness.
- Restrict branch selection to trusted operators because feature branch code runs in the Airflow/Spark environment. UAT and production refs must remain unchanged by the client.
- Verify the Docker daemon can bind-mount the run-pinned bundle checkout into the configured Spark job image. Do not use mutable `/opt/jobs` paths or injected release markers.

## Workload conventions

- Keep the three environment YAML files directly under `configs/`; do not make environment folders.
- `notebooks/common/config_loader.py` accepts only `dev`, `uat`, and `prod`, validates required `storage_path` and `database_name`, preserves arbitrary nested YAML values, and never falls back across environments.
- Export Spark code as `.py` files under `notebooks/workload/`. It must be runnable by `spark-submit` without notebook-only state.
- Git DAG Bundles select code by ref; the stable bundle name selects the DAG ID prefix and runtime environment. `lakehouse-main` (and `lakehouse-prod`) produces a `main-` DAG ID and uses the `prod` config, `lakehouse-uat` produces `uat-` and uses `uat`, and other bundle names produce `dev-` and use `dev`. The factory detects the bundle name from Airflow's `tracking_repo` parse path or versioned checkout path. Keep bundle names stable when changing the tracked branch. The shared factory builds a manual DAG (`schedule=None`), validates matching config, and uses `DockerOperator` to run `spark-submit` inside the configured Spark job image. Configure image, Spark master, Docker socket, and Docker network through the Airflow deployment environment. Keep credentials in Airflow connections or an approved secret backend.
- New Spark DAGs should call `dags/dag_factory.py` and supply only the Python entrypoint filename and schedule. The factory derives the environment, DAG ID, config, tasks, Docker/Spark settings, tags, and bundle-version behavior from the bundle checkout and shared settings.
- UAT and production share Airflow and Spark infrastructure but select their own YAML targets. Do not put credentials, tokens, or endpoints in source/YAML.
- `notebooks/workload/init_environment.py` creates the configured catalog namespace with `CREATE NAMESPACE IF NOT EXISTS`, then overwrites only `sample_spark_job_output` beneath `storage_path`. Object storage creates the prefix during the table write; the workload does not call Hadoop's S3A filesystem API to create a root directory. The path ends in `/`; the workload appends the clean table name directly.
- Use simple Spark identifier names for `database_name`; special-character quoting is outside the workload contract.

## Dev branch-selection client

Example commands:

```bash
python3 airflow_bundle_client.py --settings /etc/airflow/lakehouse/client.yml show
python3 airflow_bundle_client.py --settings /etc/airflow/lakehouse/client.yml select --branch feature/my-change
```

The client validates Git branch syntax, a required configured feature-ref prefix, and protected refs; changes only the dev bundle ref; writes the bundle config atomically; and invokes the configured argv-style apply command without a shell. It restores the previous config and invokes apply again if the requested update fails. The platform command must safely update Airflow's `dag_bundle_config_list` and reload/restart the required components. Airflow fetch/parse readiness is checked separately.

## Python conventions

- Add Google-style docstrings to generated functions/methods with applicable args, returns, and exceptions.
- Keep config validation in the shared loader; use `notebooks/common/cli.py` for standard `--environment` and `--config-dir` arguments.
- Keep test dependencies in `requirements-dev.txt`. Airflow, Spark, and provider versions belong to the external runtime; do not invent or pin them here.
- Update this guide whenever repository structure or workload/deployment contracts change.
