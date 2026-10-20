# NFR Requirements: `workload-foundation`

## Security and Data Protection
- No credentials, tokens, passwords, private keys, or other secrets may be committed to YAML, Python, DAG, Jenkins, or documentation files.
- Store Docker registry, Spark runtime credentials, and other secrets in externally managed secret facilities; do not put them in DAG source or environment YAML.
- Environment YAML contains only non-secret workload settings, including required `storage_path` and `database_name` and any additional non-secret application settings.
- The sample data is deterministic synthetic data; do not read real or sensitive source data.
- Diagnostic output may include environment name and non-secret target identifiers, but never credentials.

## Reliability and Safe Execution
- The shared configuration loader fails fast for unsupported environments, missing or malformed YAML, and missing/invalid required values. It never falls back to another environment or an implicit production default.
- The initialization DAG is manual-trigger only (`schedule=None`); it has no automatic cadence.
- A run must explicitly identify the selected environment and pass the same value to the loader and Spark workload.
- The initialization job creates the configured namespace idempotently; the table write creates its object prefix. It overwrites only the dedicated `sample_spark_job_output` table and child path; it must not delete or modify unrelated storage objects or tables.
- The runtime identity must have permission to create the namespace and write the dedicated smoke table. These permissions are external prerequisites.
- A configuration or Spark write failure must fail the Spark task and Airflow task; no partial write may be reported as successful.

## Maintainability and Testability
- Keep configuration parsing and required-key validation in the shared loader; do not duplicate YAML parsing in the DAG and Spark script.
- Preserve all additional top-level and nested YAML settings in a generic mapping API; validate only the required keys needed by the current workload so future application settings do not require loader schema changes.
- Validate that each environment file contains `storage_path` and `database_name` with valid non-empty values.
- The loader has testable invariants for environment isolation and required configuration values. Property-based tests use Hypothesis; concrete failure and sample-write scenarios remain example-based.
- No runtime version constraints were supplied. Python, Spark, Airflow, and the Airflow Spark provider are managed by the external platform; avoid pinning their versions in this repository until the platform versions are known.

## Scalability, Performance, Availability, and Usability
- **Scalability**: No scale target applies to the tiny synthetic sample workload.
- **Performance**: No latency or throughput target applies to the sample.
- **Availability / disaster recovery**: Airflow and Spark availability, backup, and recovery are owned by external platform operators; no SLO/RTO/RPO is specified here.
- **Usability / accessibility**: No user-facing interface is introduced.

## Operational Configuration
- Jenkins target endpoints, paths, and credentials remain external configuration.
- Docker daemon access, Spark image/master/network and runtime credentials remain external configuration.
- The pipeline and DAG must fail clearly when required non-secret target settings are absent, without printing secret values.
