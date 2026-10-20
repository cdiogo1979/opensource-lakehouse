# Application Design: Airflow and Spark Repository Foundation

## Purpose
Establish a maintainable repository architecture for environment-specific YAML configuration, exported Python Spark workloads, Airflow orchestration, and Jenkins branch deployment.

## Components
- **Environment Configuration**: `configs/dev.yml`, `configs/uat.yml`, and `configs/prod.yml`, each defining `storage_path` and `database_name`.
- **Shared Configuration Loader**: `notebooks/common/config_loader.py`, shared by the DAG and Spark workload to parse and validate environment YAML.
- **Shared Workload CLI**: `notebooks/common/cli.py`, reused by Spark workload entry points for standard environment/config-directory arguments.
- **Spark Workload**: Python `.py` files under `notebooks/`, run by `spark-submit` inside a Docker job image.
- **Airflow Orchestration**: One `dags/` folder sourced from versioned Git DAG Bundles; a branch-specific environment marker and shared DAG factory provide environment-prefixed identity and standard `DockerOperator` orchestration.
- **Jenkins CI and Bundle Branch Client**: Root `Jenkinsfile` runs repository checks only. `airflow_bundle_client.py` selects a feature branch for the dev bundle; UAT and production stay fixed to `uat` and `main`.

## Interfaces
- `load_environment_config(environment, config_dir) -> EnvironmentConfig` validates required `storage_path` and `database_name` values and preserves arbitrary top-level/nested YAML settings through generic mapping access.
- The Spark workload accepts the environment/config location and a cluster-provided Spark session.
- The shared factory reads the branch-specific environment marker and resolves workload/config artifacts from the same bundle version.
- Workload entry points import the standard argument parser from `notebooks/common/cli.py`.
- Airflow polls the configured Git bundle refs. The operator client modifies only the dev bundle tracking ref and delegates configuration apply/reload to the deployment platform.

## Orchestration and Dependencies
The Airflow DAG loads and validates the config from its Git bundle version, then uses `DockerOperator` to start the configured Spark job image. The container runs `spark-submit` against the matching workload and config from the mounted bundle checkout, using a deployment-configured Spark master. Jenkins gates repository CI; Airflow fetches `uat` and `main` on its configured schedule. The dev bundle tracks a feature branch selected with the operator client.

## Operational Boundaries
- No secrets, tokens, or live environment values are embedded in source or checked-in examples.
- Git connection credentials and the deployment-specific branch-client apply/reload command are external runtime configuration.
- Docker daemon access, Spark job image, network, and Spark master are supplied through the Airflow deployment environment.
- The client does not assume Airflow's UI can edit bundle refs; the target platform provides the configuration manager/reload operation.
- This design covers repository artifacts and their contracts; it does not provision Jenkins, Airflow, or Spark infrastructure.

## Supporting Artifacts
- [Component definitions](components.md)
- [Component methods](component-methods.md)
- [Services and orchestration](services.md)
- [Component dependencies](component-dependency.md)
