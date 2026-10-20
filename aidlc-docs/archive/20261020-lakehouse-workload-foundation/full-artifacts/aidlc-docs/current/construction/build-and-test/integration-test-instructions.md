# Integration Test Instructions

These checks require the Airflow 3 deployment, its Git DAG Bundle provider, Docker access, the configured Spark image/master, Nessie, and S3-compatible storage. They are not part of local pytest.

## Verify Airflow Bundle Parsing

After the configured Git bundle refreshes to the commit containing the DAG changes and `dags/.airflowignore`, run:

```sh
docker compose exec airflow-dag-processor airflow dags list -B lakehouse-main -o plain
docker compose exec airflow-dag-processor airflow dags list-import-errors
```

Confirm `main-init_environment` is loaded from the current bundle version and the import-error list has no entry for `dags/dag_factory.py` or `dags/dag_defaults.py`. Confirm stale `dev-*` DAG IDs disappear after successful parsing and Airflow's stale-DAG cleanup interval. A graphviz warning does not indicate a DAG import failure.

## Verify a Workload Run

Trigger `main-init_environment` manually in the Airflow UI or CLI. Confirm the validation task selects `configs/prod.yml`, the Docker task uses the same bundle version as the DAG run, and Spark can access the mounted bundle files, Nessie, and configured object storage. Confirm the namespace and `sample_spark_job_output` table are usable, then verify repeated execution preserves unrelated data.

Do not use production data for this smoke check. Use an isolated approved test catalog and storage target before triggering. No destructive cleanup is part of this procedure.

## Current Integration Status

The current Airflow check confirmed `main-init_environment` from bundle version `97f02ef99c507161377187b52879f2bb1c4cdc93`. It also reported an import error because Airflow parsed `dag_factory.py` as a DAG file and that direct import could not resolve `dag_defaults.py`. The repository now contains `dags/.airflowignore` to exclude the helper modules, but this local change has not yet reached the running bundle. Re-run both commands after the updated commit is fetched before treating integration as passed.
