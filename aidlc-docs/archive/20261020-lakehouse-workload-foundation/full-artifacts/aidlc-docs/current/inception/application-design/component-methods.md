# Component Methods and Interfaces

These are high-level contracts for the repository foundation. Detailed business logic is out of scope.

## Shared Configuration Loader

### `load_environment_config(environment: str, config_dir: Path) -> EnvironmentConfig`
- **Purpose**: Load the YAML file for one environment and return normalized settings.
- **Inputs**: Environment name (`dev`, `uat`, or `prod`) and configuration directory.
- **Output**: `EnvironmentConfig` with an `environment` attribute and mapping access to all YAML settings, including required `storage_path` and `database_name` plus arbitrary additional nested values.
- **Errors**: Raise a clear configuration error when the environment is unsupported, the file is missing/invalid, or a required key is absent.

## Spark Workload

### `main(environment: str, config_dir: Path, spark: SparkSession) -> None`
- **Purpose**: Load the bundle-selected environment configuration, initialize its namespace, then run the dedicated Spark smoke write (which creates the object prefix).
- **Inputs**: Environment name, configuration directory, and Spark session provided by the cluster.
- **Output**: No return value; workload effects are confined to the selected configured storage/database targets.
- **Errors**: Surface invalid configuration and Spark execution failures to the submitting task.

## Airflow Orchestration

### `create_spark_dag(entrypoint_file: str, schedule: str | None) -> DAG`
- **Purpose**: Build the standard environment-validation and Docker Spark submission DAG.
- **Inputs**: Workload entrypoint filename and Airflow schedule; environment is read from the bundle's branch-specific marker.
- **Output**: DAG with shared IDs/settings and validation/submission tasks.
- **Errors**: Surface invalid marker, missing workload entrypoint, DAG import errors, and runtime config/Spark failures.

## Dev Bundle Branch Client

### `show_selected_ref(config_path: Path) -> str`
- **Purpose**: Read the current `lakehouse-dev` tracking ref from the deployment-managed bundle config.
- **Errors**: Report malformed/missing bundle configuration without modifying it.

### `select_dev_ref(settings: Mapping[str, Any], tracking_ref: str) -> tuple[str, str]`
- **Purpose**: Validate a Git branch, update only `lakehouse-dev.tracking_ref`, write the config atomically, and invoke the configured platform apply/reload command.
- **Errors**: Reject protected refs and invalid configuration; restore the previous config/ref if apply fails.
- **Constraint**: Invoke the external command as an argv list without shell evaluation. Do not log secrets or claim Airflow bundle fetch/parse readiness.
