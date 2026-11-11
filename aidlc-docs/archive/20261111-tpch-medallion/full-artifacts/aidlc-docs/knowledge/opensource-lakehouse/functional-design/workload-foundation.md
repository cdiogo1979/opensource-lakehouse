# Workload Foundation Functional Design

## Environment configuration

Keep `dev.yml`, `uat.yml`, and `prod.yml` directly in `configs/`. The current workload requires `storage_path` and `database_name`; the loader rejects unsupported environments, missing or invalid files, malformed YAML, non-mapping roots, and invalid required values. It preserves arbitrary additional top-level and nested settings through a generic read-only mapping, and offers a mutable deep-copy conversion when needed. It does not fall back to another environment. Secrets and runtime credentials are external.

`storage_path` is expected to end in `/`, and `database_name` is assumed to be a clean simple Spark identifier. These are the current workload assumptions; special identifier quoting/path normalization is outside the contract.

## Spark initialization workload

`notebooks/workload/init_environment.py` loads the selected config using the common CLI. It issues `CREATE NAMESPACE IF NOT EXISTS` for the configured database/catalog namespace and then writes two deterministic synthetic rows to `sample_spark_job_output` using overwrite mode. The output path is `storage_path + "sample_spark_job_output"`. Only this dedicated table/path may be overwritten. The job does not delete unrelated tables or objects.

The workload does not create an S3 directory marker through Hadoop S3A. The table write creates the object keys/prefix; this avoids requiring `S3AFileSystem` merely to initialize a path. Errors propagate to Airflow.

## Airflow DAG behavior

The thin declaration `dags/init_environment.py` supplies the Python entrypoint and manual schedule. `dags/dag_factory.py` and `dag_defaults.py` select environment/config and DAG prefix from the bundle checkout identity, validate configuration, and construct the standard DAG and Docker Spark task. Helper files are excluded from discovery by `.airflowignore` but remain importable by the declaration.

`lakehouse-main`/`lakehouse-prod` selects `prod.yml` and a `main-` DAG prefix; `lakehouse-uat` selects `uat.yml` and `uat-`; other names select `dev.yml` and `dev-`. The Docker task mounts the bundle checkout read-only and uses the same version as the DAG run. Airflow image, master, Docker endpoint/network, AWS region, and service credentials are deployment inputs.

## Invariants and failure behavior

- Environment selection is explicit from bundle identity; config loading never silently falls back.
- Repeated namespace initialization is safe.
- The only overwrite is the named synthetic smoke table at its dedicated child path.
- Unrelated catalog/storage state remains unchanged.
- Config, import, mount, catalog, or storage failures fail the Airflow task and remain visible in logs.
- Integration against the live `.airflowignore` update and Spark/Nessie/S3 was not completed in this intent; see the archived Build and Test record.
