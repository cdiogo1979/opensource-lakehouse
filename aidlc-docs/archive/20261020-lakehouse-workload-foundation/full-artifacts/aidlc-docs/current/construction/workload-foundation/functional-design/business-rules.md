# Business and Validation Rules: `workload-foundation`

## Environment Configuration Rules
1. Supported environment identifiers are exactly `dev`, `uat`, and `prod`.
2. Each environment has one YAML file directly under `configs/`: `dev.yml`, `uat.yml`, or `prod.yml`.
3. Each file must provide non-empty string values for `storage_path` and `database_name`; `database_name` is a simple Spark identifier without special characters.
4. The loader must reject an unsupported environment, missing file, malformed YAML, non-mapping YAML root, absent required key, or empty/non-string required value.
5. The loader fails immediately with a clear error identifying the environment, file, or key issue. It must not silently default or fall back to another environment.
6. The loader preserves all additional top-level and nested YAML settings without requiring a fixed schema or code change; consumers access them through the generic `EnvironmentConfig` mapping.
7. Configuration files do not contain secrets, tokens, or credentials.

## Environment Initialization Rules
1. The workload is named `init_environment` and initializes only the namespace and smoke table selected by the loaded environment configuration.
2. Create the configured catalog namespace with `CREATE NAMESPACE IF NOT EXISTS`. An existing namespace is accepted without recreation or deletion.
3. Object storage does not require an empty directory/root marker. The table write creates the necessary object prefix; do not call Hadoop's S3A filesystem API just to create the configured root.
4. Namespace initialization is repeatable: a second run against the same environment accepts the existing namespace.
5. The configured storage root ends with `/`. The smoke output location is `storage_path + "sample_spark_job_output"`.
6. After namespace initialization, write the tiny deterministic synthetic dataset to the dedicated `sample_spark_job_output` table in the configured database. Use overwrite mode only for this table and its dedicated child location.
7. No other table or data path may be created, overwritten, or deleted by this workload.
8. The Spark identity must have permission to create the namespace and write the dedicated smoke table. Missing permissions or failed operations fail the Spark task and Airflow task; partial success must not be reported as successful completion.
9. If namespace initialization fails, do not continue to the smoke write. If the smoke write fails, report task failure.

## DAG Rules
1. Keep one DAG source under `dags/`. The Airflow bundle name selects the environment: `lakehouse-main` and `lakehouse-prod` use `main` as the DAG ID prefix and `prod` config; `lakehouse-uat` uses the `uat` prefix and config; all other bundle names use `dev` prefix and config.
2. Airflow reads the same DAG path from each GitDagBundle ref. Bundle identity selects environment and prefix: `lakehouse-main`/`lakehouse-prod` → `prod` config with `main-` DAG IDs, `lakehouse-uat` → `uat`, and other names → `dev`.
3. DAG code resolves config, helpers, and Spark application relative to the repository root in the bundle version that supplied the DAG. No release marker or mutable `/opt/jobs` path is used.
4. Keep bundle versioning enabled so a DAG run uses the same Git commit for DAG, config, helpers, and Spark application.
5. The DAG launches the configured Spark job image with `DockerOperator`; its `spark-submit` command uses the run-pinned bundle code/config and a deployment-configured Spark master. Credentials are provided externally, not embedded in DAG source.
6. A DAG declaration supplies only its Python entrypoint filename and schedule; `dags/dag_factory.py` selects the environment from its versioned bundle checkout path and creates the standard config-validation and Docker Spark tasks, while `dags/dag_defaults.py` centralizes standard Airflow DAG settings. `.airflowignore` excludes those helper modules from DAG discovery.
