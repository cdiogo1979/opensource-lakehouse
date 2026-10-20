# Proposed Pull Request

## Title

Add environment-configured Spark workloads and Airflow Git Bundle deployment

## Problem

The lakehouse repository needed a consistent layout for environment configuration, Python Spark workloads, and Airflow DAGs. Workloads must consume environment-specific values without embedding them in code. Airflow must run code and config from the same Git revision, support feature-branch testing, and avoid Jenkins file-copy deployment.

## Solution

Establish `configs/`, `notebooks/`, and `dags/` as the repository's workload foundation. Store one YAML file per environment with required `storage_path` and `database_name` values. A reusable loader validates those required settings while preserving arbitrary additional keys and nested values; a shared CLI supplies environment/config-directory arguments to Spark jobs.

Use Airflow 3 Git DAG Bundles to fetch versioned repository refs. A shared DAG factory keeps individual DAG declarations small, validates the selected config, and launches the Python Spark entrypoint with `DockerOperator` and `spark-submit`. The stable bundle name selects the config and DAG ID prefix: `lakehouse-main`/`lakehouse-prod` maps to `prod.yml` with a `main-` ID, `lakehouse-uat` maps to `uat.yml` with a `uat-` ID, and other names (including `lakehouse-dev`) map to `dev.yml` with a `dev-` ID.

Provide an operator CLI to change only the development bundle's tracking ref to an allowed feature branch. Jenkins remains a CI gate and does not publish DAG or workload files. The `init_environment` workload creates the configured namespace if absent and overwrites only its dedicated synthetic smoke table; the table write creates the object-store prefix.

## Main changes

- `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml`: per-environment storage and database settings, with no credentials.
- `notebooks/common/config_loader.py`: shared strict YAML loading for required values and generic access to arbitrary nested configuration.
- `notebooks/common/cli.py`: reusable `--environment` and `--config-dir` parsing.
- `notebooks/workload/init_environment.py`: idempotent namespace initialization and a deterministic, narrowly scoped Spark smoke write.
- `dags/init_environment.py`, `dags/dag_factory.py`, `dags/dag_defaults.py`, `dags/.airflowignore`: thin DAG declaration, shared Docker/Spark orchestration and defaults, bundle-name mapping, and helper discovery exclusion.
- `airflow_bundle_config.example.json`, `airflow_bundle_client.py`, `airflow_bundle_client.example.yml`, `AIRFLOW_BUNDLES.md`: three-bundle configuration example, guarded dev-ref selection CLI, non-secret settings example, and operator setup guidance.
- `Jenkinsfile`: syntax/compile and unit-test CI only; no SFTP or upload publisher.
- `tests/`, `requirements-dev.txt`, `pyproject.toml`, `scripts/code_quality.sh`: unit/property coverage and Python quality tooling. Black runs in formatting mode.
- `AGENTS.md` and AI-DLC artifacts: repository conventions, design decisions, verification results, and deployment handoff.

## Verification

- Compile validation: passed after Black formatting.
- Unit/property tests: 48 passed after Black formatting.
- Ruff and Black: passed.
- Flake8: two `E203` warnings remain.
- Bandit: 67 low-severity findings remain, primarily test assertions and a test subprocess import.
- Airflow: `main-init_environment` was observed in bundle `lakehouse-main`, but the checked live bundle had an import error while parsing `dag_factory.py`. The `.airflowignore` fix has not yet been fetched and rechecked.
- Spark/Nessie/object-storage integration was not run.

**Verification waiver accepted by the user for continuing the AI-DLC process**: the outstanding Flake8/Bandit findings and unverified Airflow/Spark integration are recorded as limitations, not passing checks. Resolve or explicitly retain these limitations before release.

## Deployment

This change requires ordered platform configuration and validation. See [deploy_instructions.md](deploy_instructions.md). This is a proposed PR description only; no PR was created, and no deployment or push was performed.

## Risks and limitations

- The repository's example config includes local RustFS/Nessie values. Confirm environment targets before any DAG run; `init_environment` overwrites only the configured `sample_spark_job_output` table.
- The current Airflow check showed a `lakehouse-main` bundle; the example deployment config defines `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod`. Confirm and apply the intended bundle names and their mappings in the deployment configuration.
- The Airflow parse fix must reach the bundle and be rechecked. Provider versions, bundle refresh, Docker mount access, Spark connectivity, and external credentials remain platform prerequisites.
- The dev branch-selection client requires an operator-managed config path, allowed feature-branch prefixes, and a trusted platform-specific apply/reload command.
- Flake8 and Bandit findings remain. The accepted waiver records their status; it does not establish that scans or runtime verification passed.
- The current workspace changes are based on `main` at `97f02ef`; they have not been committed or pushed.
