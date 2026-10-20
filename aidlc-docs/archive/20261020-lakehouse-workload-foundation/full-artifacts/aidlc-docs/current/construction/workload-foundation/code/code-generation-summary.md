# Code Generation Summary: `workload-foundation`

## Generated Files

- `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml` — Environment-specific `storage_path` and `database_name` examples.
- `notebooks/common/config_loader.py` — Strict environment YAML loader with an immutable generic mapping that preserves arbitrary nested values.
- `notebooks/common/cli.py` — Shared parser for standard `--environment` and optional `--config-dir` arguments.
- `notebooks/workload/init_environment.py` — Creates the configured namespace idempotently, then writes the deterministic two-row synthetic smoke table at its dedicated child path. The object prefix is created by the write; no Hadoop S3A filesystem API is called just to create an object-store directory.
- `dags/init_environment.py` — Thin DAG declaration that supplies the `init_environment.py` entrypoint and manual schedule.
- `dags/.airflowignore` — Excludes DAG helper modules from Airflow DAG discovery while leaving them importable from the declaration.
- `dags/dag_defaults.py` — Derives the DAG ID prefix and workload config environment from the versioned bundle checkout path and centralizes standard Airflow DAG arguments.
- `dags/dag_factory.py` — Builds the common config-validation and Docker Spark submission tasks from an entrypoint filename and schedule.
- `requirements-dev.txt` — PyYAML, pytest, and Hypothesis development/test dependencies.
- Workload foundation tests — Loader behavior, config isolation, shared DAG defaults, initialization and smoke-write contracts, and property-based coverage.
- `AGENTS.md` — Repository layout and workload conventions, synchronized with Git Bundle deployment.

## Configuration and Runtime Inputs

The three YAML files contain conspicuous placeholder bucket and database values. Replace them with approved S3 locations and catalog/database names for each environment before a run. Do not treat placeholders as deployable values.

The shared factory maps `lakehouse-main` and `lakehouse-prod` to the `main` DAG prefix and `prod.yml`, `lakehouse-uat` to `uat` and `uat.yml`, and every other bundle name to `dev` and `dev.yml`. Airflow must install compatible Docker and Git bundle providers; the Spark runtime must have compatible PyYAML and S3 filesystem support and accept the submitted script, shared loader, CLI helper, and selected environment config. Namespace-creation permissions, AWS authorization, connection credentials, and network access are external prerequisites.

Applications can read settings with `config["storage_path"]`, `config.get("database_name")`, or nested access such as `config["spark"]["executor"]["memory"]`. `config.to_dict()` returns a mutable deep copy when an integration needs ordinary dictionaries and lists.

`database_name` values are assumed to be simple Spark identifiers without special characters; the workload builds the namespace and qualified table names directly. `storage_path` values must end in `/`; the workload appends `sample_spark_job_output` directly. Object storage has no directory that needs pre-creation; writing the dedicated table creates its object prefix.

## Traceability

- **FR-1**: Three per-environment YAML files with the required non-secret keys and generic nested settings.
- **FR-2/NFR-5**: Exported Python Spark initialization job with configuration externalized, idempotent namespace/root setup, and a narrowly scoped smoke write.
- **FR-3**: Thin DAG declarations in root `dags/` specify a job entrypoint and schedule. A shared factory reads the bundle identity, creates unique prefixed DAG IDs, validates config, launches the configured Spark image, and mounts the run's bundle checkout read-only.
- **FR-4**: Bundle delivery and the development feature-branch client are detailed in the `jenkins-deployment` unit.
- **FR-5 (Unit 1 portion)**: Repository structure and workload conventions are documented in `AGENTS.md`.
- **NFR-1/NFR-2**: Secrets remain external; config loading and validation are shared.
- **NFR-4/PBT-01**: Example tests and Hypothesis properties cover config validity, environment isolation, nested YAML preservation, namespace idempotence, preservation of unrelated state, and the smoke-write boundary. Build and Test reports 48 passing tests.

## External Prerequisites and Limitations

- Concrete S3 bucket/prefixes, database/catalog names, Docker daemon endpoint, Spark image/master/network are not supplied.
- The Docker daemon must see the Git bundle version's checkout path to mount the DAG's matching config, helpers, and Spark application into the job container. This is an integration verification gate for Build and Test.
- The Spark cluster, catalog, S3 connector, identity permissions, and runtime versions are not provisioned here.
- Airflow bundle parsing found the expected `main-init_environment` DAG, but also reported an import error when parsing `dag_factory.py` directly. `dags/.airflowignore` was added locally to exclude helper modules; this fix has not yet reached the running bundle and must be verified after the bundle refreshes. Spark and catalog integration was not run in this stage.
