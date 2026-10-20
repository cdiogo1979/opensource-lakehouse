# Infrastructure Design: `workload-foundation`

## Scope and Decisions

- UAT and production use the same externally managed Airflow and Spark infrastructure.
- The selected environment YAML separates their data targets through `storage_path` and `database_name`.
- S3-compatible object storage is the storage backend. Bucket names, paths, AWS account/region, and URI scheme remain deployment configuration because they were not provided.
- Development infrastructure topology was not specified and remains an external deployment input.
- This repository provides configuration, the environment initialization workload, and the Airflow DAG. It does not provision or administer Airflow, Spark, S3-compatible storage, IAM, the Nessie service, or networks.

## Component to Infrastructure Mapping

| Repository component | Infrastructure boundary | Responsibility and requirements |
|---|---|---|
| `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml` | Version-controlled repository content | Non-secret environment settings. UAT and production values must point to their intended isolated S3 locations and databases/catalog namespaces. |
| Shared config loader | Airflow DAG and submitted Spark application | Reads only the explicitly selected environment file, validates required `storage_path` and `database_name`, and preserves arbitrary additional top-level and nested settings through a generic mapping. The loader must be packaged or otherwise made available to the Spark runtime during submission. |
| Airflow DAG | Shared Airflow 3 service with Git DAG Bundles | Manual execution via `DockerOperator`; the bundle name selects the config environment and DAG ID prefix. Airflow records bundle version, task state, and logs. |
| Docker/Spark runtime | Docker daemon and configured Spark job image | Runs `spark-submit` with the run-pinned bundle checkout mounted read-only; image, master, network, daemon endpoint, and credentials are deployment inputs. |
| Spark workload | Shared external Spark service | Executes the Python workload, initializes the configured namespace, and writes only the dedicated smoke table/path. |
| S3-compatible storage | External object storage | Stores the smoke output beneath the configured environment root. The Spark runtime must have a compatible Hadoop filesystem connector and authorization. |
| Nessie catalog | External Spark catalog | The workload creates the configured namespace if missing; the Spark identity needs namespace and dedicated smoke-table permissions. |

## Environment Isolation and Safety

Airflow and Spark are shared for development, UAT, and production. Each Git bundle checks out the same root `dags/`, `configs/`, and `notebooks/` paths from its own ref. The bundle name maps to environment: `lakehouse-main`/`lakehouse-prod` to `prod`, `lakehouse-uat` to `uat`, all other names to `dev`. Each DAG run records the bundle's Git commit so config and Spark code come from that same versioned checkout. Operators must ensure that UAT and production config files identify distinct, authorized data targets; no run-time environment override or fallback is permitted.

The `init_environment` workload creates `database_name` using `CREATE NAMESPACE IF NOT EXISTS`, ensures the configured `storage_path` exists through Hadoop filesystem APIs without modifying existing contents, then writes `database_name.sample_spark_job_output` in overwrite mode to `storage_path` followed directly by `sample_spark_job_output`. Each configured `storage_path` must end in `/`. The Spark identity must be scoped to the intended environment data locations and table permissions. The configured root itself and unrelated paths must not be overwritten.

Credentials, access keys, tokens, and deployment endpoints do not belong in the YAML files or DAG parameters. Airflow connection secrets and AWS authorization are supplied through externally managed connections, secret backends, or the Spark platform's approved identity mechanism. Logs may identify the selected environment and non-secret configuration but must not expose credentials.

## Runtime and Operations

- Airflow must have the Spark provider/operator and a working connection to the shared Spark service.
- The Spark runtime must support the submitted Python code, YAML loader dependency, the shared config loader, and the S3 connector compatible with the configured URI form. Verify that the selected Airflow executor and Spark submission host can access or stage the bundle-versioned files selected by the DAG.
- The Spark execution identity must be authorized for the selected S3 path and catalog/database operations.
- Airflow task state and logs provide orchestration visibility; Spark execution logs remain on the external Spark platform.
- Runtime versions, availability, sizing, network topology, S3 bucket lifecycle, encryption policy, and alerting are owned by platform operators because no specific requirements or platform details were provided.

## Deployment Inputs Still Required

Before deploying/running against an environment, operators must supply its concrete S3 location and database/catalog name, provision the required S3 connector and identity permissions, configure the Docker daemon, Spark job image/master/network, and enable Git bundle access to the selected branch/version. Verify that the Docker daemon can mount the exact bundle checkout during Build and Test.

For development, the Airflow/Spark target, selected feature branch, and access configuration remain deployment inputs.
