# Component Dependencies and Data Flow

## Dependency Matrix

| Consumer | Depends on | Communication / contract |
|---|---|---|
| Shared Configuration Loader | `configs/<environment>.yml` | Reads full YAML mapping; requires `storage_path` and `database_name`, and preserves arbitrary other settings. |
| Spark Workload | Shared Configuration Loader; Spark runtime | Calls loader; uses the Spark session supplied by the cluster. |
| Airflow DAG | Shared Configuration Loader; Docker daemon; Spark Workload | Loads environment settings, bind-mounts the run's bundle checkout, and runs the script and loader inside the configured Spark job image through `DockerOperator`. |
| Airflow Git Bundles | Git repository branches and Airflow Git connection | Fetches each configured ref, parses environment DAGs, and records the bundle commit for each DAG run. |
| Dev branch client | Operator-selected branch; deployment config; apply/reload command | Changes only `lakehouse-dev.tracking_ref`, then invokes the external deployment configuration manager. |
| Jenkins CI | Repository checkout | Runs validation/tests and branch gates; does not transfer artifacts or manage Airflow Git credentials. |

## Data and Configuration Flow
1. `configs/dev.yml`, `configs/uat.yml`, or `configs/prod.yml` provides non-secret environment settings.
2. The shared loader validates required keys and exposes the full environment mapping to the DAG and Spark workload.
3. The DAG submits the Spark script and shared loader dependency to the external cluster.
4. Airflow tracks the dev feature ref selected by the client, while UAT and production remain fixed to `uat` and `main`; each bundle includes its environment DAGs and shared config/workload directories.

## Boundary Rules
- The YAML files contain environment values, never credentials or tokens.
- The shared loader owns parsing and required-key validation; the DAG and workload do not implement separate YAML parsing.
- The DAG owns scheduling and Docker/Spark launch configuration, not data transformation logic.
- The client owns dev ref selection; Airflow owns branch fetch, DAG parsing, and run-version pinning. Runtime configuration apply/reload and Spark provisioning remain external.
