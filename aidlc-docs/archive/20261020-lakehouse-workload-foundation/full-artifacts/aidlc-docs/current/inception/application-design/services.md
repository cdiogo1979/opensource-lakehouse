# Services and Orchestration

## Configuration Loading
The shared loader resolves `configs/<environment>.yml`, parses the complete YAML mapping, validates required `storage_path` and `database_name`, and returns all settings through the same generic mapping contract to the Airflow DAG and Spark entry point.

## Spark Submission
Airflow selects the environment for a DAG run and uses `DockerOperator` to launch the configured Spark job image. The container runs `spark-submit` with the workload, shared loader, and environment config from the run-pinned bundle checkout, using the deployment-configured Spark master. Credentials remain outside the DAG source.

## Git Bundle Delivery and Branch Selection
Airflow polls versioned Git DAG Bundles. The development bundle tracks the feature branch selected by `airflow_bundle_client.py`; UAT tracks `uat`; production tracks `main`. Each bundle checks out the same `dags/`, `configs/`, and `notebooks/` paths from its branch. The bundle name provides environment identity to the shared factory (`lakehouse-main`/`lakehouse-prod` → `prod`, `lakehouse-uat` → `uat`, all others → `dev`). Jenkins runs CI checks and gates UAT/production changes but does not publish artifacts.

## Sequence
1. A trusted operator selects a feature branch for `lakehouse-dev` with the branch-selection client. The client applies the deployment config and requests the required reload/restart.
2. Airflow fetches the selected ref and parses the development DAG; UAT and production remain on their fixed refs.
3. A DAG run records the bundle commit version and selects its environment.
4. Airflow submits the matching Spark application, shared loader, and config from that bundle version to the external cluster.

The Git connection, dev-ref apply/reload command, Airflow bundle refresh, and Spark cluster connection are configured outside the repository. Jenkins does not deploy to Airflow.
