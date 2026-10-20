# Business Logic Model: `workload-foundation`

## Scope
This unit implements configuration selection/validation and an idempotent environment initialization job with a small Spark smoke write. It has no business-domain transformations.

## Configuration Loading Flow
1. The selected Git bundle checkout path identifies the environment: `lakehouse-main` and `lakehouse-prod` map to `prod`, `lakehouse-uat` maps to `uat`, and all other bundle names map to `dev`. Local non-bundle DAG paths map to `dev`.
2. The selected bundle commit supplies the DAG, matching root `configs/<environment>.yml`, shared helpers, and Spark workload. No injected release ID or mutable shared release path is used.
3. The loader parses the complete YAML mapping, validates required `storage_path` and `database_name`, and returns an immutable generic `EnvironmentConfig` mapping that preserves other top-level and nested values.
4. The shared DAG factory validates and submits the workload with the marker-selected environment and makes the matching shared loader available to the Spark runtime.
5. The `init_environment` workload loads the same environment config from the run's bundle version.

## Initialization and Smoke-Write Flow
1. Load and validate the selected environment configuration before performing side effects. Use its `database_name` as the target catalog namespace and its `storage_path` as the target logical root/prefix.
2. Request namespace creation with `CREATE NAMESPACE IF NOT EXISTS <database_name>`. Existing namespace state is accepted.
3. Do not pre-create an object-store storage root with Hadoop filesystem APIs. Writing the dedicated smoke table creates its object prefix; preserve all existing and unrelated objects.
4. After both initialization operations succeed, create/write the dedicated `database_name.sample_spark_job_output` smoke table at `storage_path + "sample_spark_job_output"`; `storage_path` is assumed to end with `/`.
5. Write the fixed tiny synthetic dataset in overwrite mode, scoped only to that dedicated table/location. This retained write verifies that catalog and storage access work end to end.
6. Propagate configuration, namespace, filesystem, or Spark write failures to the Airflow task. Do not report success after a failed step, and do not attempt the smoke write if namespace or root initialization fails.

No unrelated database, table, or path is modified. Environment config values are not secrets and may be logged for diagnostics; credentials and tokens must never be logged.

## Testable Properties (PBT-01)
- **Invariant**: For every supported environment with valid YAML, the loader returns non-empty `storage_path` and `database_name` values from that environment's file. Category: invariant/type preservation.
- **Invariant**: Any additional top-level or nested YAML setting is preserved and accessible through mapping and nested mapping access, without a loader schema change. Category: invariant/type preservation.
- **Invariant**: Loading one environment never returns values from a different environment file. Category: invariant.
- **Idempotence**: Repeating the deterministic sample write with the same configuration yields the same dedicated table contents because the write mode is overwrite. Category: idempotence; exercise through a generated-input writer contract test, with the real Spark service retained as an external integration prerequisite.
- **Idempotence**: Applying initialization repeatedly to the same catalog state leaves the configured namespace present, rewrites only the dedicated smoke table, and leaves unrelated state unchanged. Category: idempotence and invariant; exercise against a generated-input state model and catalog test doubles.
- **Scope invariant**: For every valid generated configuration, namespace creation targets exactly `database_name`, root initialization targets exactly `storage_path`, and the only overwrite target is `storage_path + "sample_spark_job_output"` / `database_name.sample_spark_job_output`.
- **Ordering invariant**: The smoke write is attempted only after namespace and root initialization succeed; failures in either initialization step are propagated and prevent later steps.
- **Error property**: Unsupported environments, missing files, invalid YAML, or missing required keys fail without silently substituting another environment or defaults. Category: invariant over invalid inputs; generated invalid required values and missing selected files are covered by Hypothesis, with malformed YAML and fixed boundary cases pinned by example-based tests.
- The sample dataset is fixed and intentionally small; its schema and row count are checked as example-based behavior. No generated-input property is needed for the data itself.
- **Not applicable**: No inverse serialization operation, competing reference algorithm, or mutable in-process state machine exists in this unit.
