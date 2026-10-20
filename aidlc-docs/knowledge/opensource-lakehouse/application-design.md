# Open Source Lakehouse Application Design

## Purpose and boundaries

This repository holds non-secret environment configuration, exported Python Spark workloads, and Airflow DAG sources. Airflow 3 Git DAG Bundles fetch versioned repository refs. A DAG validates environment configuration, then uses `DockerOperator` to launch the configured Spark job image and run `spark-submit`. The Spark workload uses Nessie-compatible catalog operations and S3-compatible storage. Jenkins runs compile and unit-test CI; it does not publish files to Airflow or change bundle refs.

Airflow, its Git/Docker providers, the Docker daemon, Spark, Nessie, S3-compatible storage, runtime credentials, bundle configuration, and deployment reload behavior are externally managed.

## Repository components

| Component | Responsibility |
|---|---|
| `configs/` | One YAML file for `dev`, `uat`, and `prod`; `storage_path` and `database_name` are required. Additional top-level and nested application settings are allowed. Secrets are external. |
| `notebooks/common/config_loader.py` | Strictly load an explicitly selected YAML mapping, validate the required current workload keys, and preserve arbitrary nested values for applications. |
| `notebooks/common/cli.py` | Parse standard `--environment` and optional `--config-dir` arguments for Spark entrypoints. |
| `notebooks/workload/` | Exported Python Spark jobs, runnable with `spark-submit`. |
| `dags/` | Thin DAG declarations, shared defaults/factory, and `.airflowignore` rules for helpers. |
| `airflow_bundle_client.py` | Trusted operator CLI that changes only `lakehouse-dev.tracking_ref` to an allowed feature branch and invokes an externally configured apply/reload command. |
| `Jenkinsfile` | Compile and unit-test CI only. |

## Airflow bundle contract

The example deployment has three stable bundles: `lakehouse-dev` follows an operator-selected feature branch, `lakehouse-uat` tracks `uat`, and `lakehouse-prod` tracks `main`. Each checks out the same root paths `dags/`, `configs/`, and `notebooks/`; a run must use the DAG, config, helpers, and Spark application from its recorded bundle commit.

Bundle name selects runtime config and DAG ID prefix:

| Bundle name | Config | DAG ID prefix |
|---|---|---|
| `lakehouse-main` or `lakehouse-prod` | `prod.yml` | `main-` |
| `lakehouse-uat` | `uat.yml` | `uat-` |
| Other names, including `lakehouse-dev` | `dev.yml` | `dev-` |

The current observed local Airflow instance used `lakehouse-main`. The config example uses `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod`; deployers must keep bundle names and the mapping intentional.

The DAG factory validates the selected YAML, then submits the configured entrypoint through `DockerOperator` and `spark-submit`. The Docker daemon must see the same pinned bundle checkout path resolved by Airflow. `.airflowignore` prevents helper modules from being parsed as DAG declarations.

## Security and operations

Git credentials and runtime AWS/S3 credentials belong in Airflow connections or an approved secrets backend. Repository config, example bundle JSON, client settings, and DAGs contain no secret values. Feature branches execute with Airflow/Spark privileges, so branch selection is restricted to trusted operators and configured prefixes. UAT and production refs are not changed by the client.

The Spark image, master, Docker socket/network, Airflow provider versions, bundle refresh interval, Git connection, target paths/database names, and apply/reload command are deployment inputs. Integration validation must confirm DAG parsing, bundle-version consistency, Docker mount visibility, Nessie connectivity, and S3 access before environment use.
