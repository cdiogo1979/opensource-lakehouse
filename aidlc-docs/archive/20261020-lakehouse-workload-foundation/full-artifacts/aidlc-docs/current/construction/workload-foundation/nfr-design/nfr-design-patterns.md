# NFR Design Patterns: `workload-foundation`

## Configuration Safety
- The Git bundle name declares its environment: `lakehouse-main`/`lakehouse-prod` select `prod`, `lakehouse-uat` selects `uat`, and all other bundle names select `dev`. Only `lakehouse-main`/`lakehouse-prod` receive the `main` DAG ID prefix.
- The shared loader resolves only the matching `configs/<environment>.yml` file, validates required `storage_path` and `database_name`, and preserves arbitrary additional top-level and nested settings for application access.
- Validation errors identify the missing/invalid environment, file, or key without logging secrets.

## Safe Initialization and Smoke Writes
- The DAG has `schedule=None`; the sample is run only by an explicit manual trigger.
- The task sets one automatic retry (`retries=1`). Namespace creation uses `IF NOT EXISTS`; storage-root initialization leaves existing contents untouched; and the deterministic smoke dataset overwrites only `sample_spark_job_output` at its dedicated path, so a retry repeats the same bounded operation.
- Namespace creation, storage-root access, and smoke-table permissions are runtime requirements. Failure in any initialization or write step is surfaced as task failure; the DAG does not report success after a failed Spark submission.
- The sample output path must be derived beneath the configured storage root and must never resolve to the root or an unrelated data location.

## Credential and Secret Handling
- Docker daemon access and Spark container settings are supplied through Airflow deployment configuration; Spark runtime credentials are provided through a secret backend or workload identity and never embedded in the DAG.
- Jenkins credentials and deployment targets remain in Jenkins-managed configuration; no secret or deployment endpoint is included in this unit's code.
- DAG parameters and logs may contain the environment name and non-secret settings only. Never log credentials, tokens, or secret backend values.

## Runtime Compatibility
- Python, Spark, Airflow, and provider versions are managed by the external platform and are not pinned in this repository.
- Use stable public APIs for `DockerOperator`, PyYAML, and the configured Spark runtime. Platform compatibility and Docker host path mapping are verified against the actual runtime during integration.

## Not Applicable
- **Scalability**: Tiny synthetic sample, no growth or throughput requirement.
- **Performance**: No latency/throughput target.
- **Availability and disaster recovery**: Owned by external Airflow and Spark operators; no SLO/RTO/RPO supplied.
- No cache, queue, circuit breaker, or new infrastructure service is required.
