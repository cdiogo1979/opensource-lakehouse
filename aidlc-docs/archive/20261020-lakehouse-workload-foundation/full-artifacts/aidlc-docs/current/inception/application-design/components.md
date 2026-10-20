# Component Definitions

## Environment Configuration
- **Purpose**: Hold non-secret settings separately for `dev`, `uat`, and `prod`.
- **Location**: `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml`.
- **Responsibilities**: Define required `storage_path` and `database_name` plus any additional application-specific top-level or nested settings; remain the source of environment-specific workload settings.
- **Interface**: YAML document with required string keys `storage_path` and `database_name`; additional keys and nested mappings are permitted and preserved.

## Shared Configuration Loader
- **Purpose**: Load and validate environment YAML consistently in the Airflow DAG and Spark workload.
- **Location**: `notebooks/common/config_loader.py`.
- **Responsibilities**: Resolve the requested environment file, parse YAML, validate required keys, and return the complete settings through a generic read-only mapping. It must preserve unrecognized settings and must not resolve secrets.
- **Interface**: `load_environment_config(environment, config_dir) -> EnvironmentConfig`.

## Shared Workload CLI
- **Purpose**: Reuse standard command-line parsing across exported Spark workloads.
- **Location**: `notebooks/common/cli.py`.
- **Responsibilities**: Parse explicit `--environment` and optional `--config-dir` arguments without duplicating parser definitions in each workload.
- **Interface**: `parse_args(argv) -> argparse.Namespace`.

## Spark Workload
- **Purpose**: Contain Python Spark code exported from Jupyter notebooks and run with `spark-submit` inside a Docker job image.
- **Location**: `notebooks/`.
- **Responsibilities**: Accept an environment identifier; use the shared loader to access required and application-specific settings; idempotently initialize the configured catalog namespace, then execute the dedicated smoke write.
- **Interface**: Command-line entry point receiving environment/config location and a Spark session supplied by the cluster runtime.

## Airflow Orchestration
- **Purpose**: Schedule and coordinate Spark workloads.
- **Location**: One `dags/` folder, delivered through versioned Git DAG Bundles.
- **Responsibilities**: The branch-specific marker supplies environment identity; a shared factory builds standard DAG settings and tasks, resolves config/Spark code from the recorded bundle version, and launches the job image with `DockerOperator`.
- **Interface**: Airflow GitDagBundle, Docker daemon, configured Spark image/master/network; no credentials are embedded in source.

## Jenkins CI and Dev Bundle Branch Client
- **Purpose**: Validate repository changes and let a trusted operator select the feature branch tested by Airflow's dev bundle.
- **Location**: Root `Jenkinsfile` and `airflow_bundle_client.py`.
- **Responsibilities**: Jenkins runs source checks only. The CLI changes only `lakehouse-dev.tracking_ref`, applies the deployment-managed bundle config, and invokes the platform reload/restart operation. UAT and production refs remain fixed to `uat` and `main`.
- **Interface**: CLI uses a non-secret settings file and argv-style apply command. Git credentials and runtime configuration manager are external platform inputs.
