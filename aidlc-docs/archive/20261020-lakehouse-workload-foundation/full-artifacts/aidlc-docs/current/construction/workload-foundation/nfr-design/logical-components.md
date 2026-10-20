# Logical Components: `workload-foundation`

| Component | Responsibility | NFR design behavior |
|---|---|---|
| Environment YAML | Store non-secret settings per environment | One file per environment; values are explicitly selected; no credential material. |
| Shared config loader | Parse and validate YAML for DAG and Spark workload | Fail fast on unsupported environment, missing/invalid file, or missing/invalid required key; preserve all other top-level and nested YAML settings through a generic read-only mapping. |
| Airflow DAG and factory | Manual orchestration and task status | Bundle name selects the environment; factory applies standard settings, creates a prefixed DAG ID, validates config, and submits the workload; one retry for the deterministic dedicated overwrite. |
| Docker daemon and Spark job image | Launch isolated Spark submission container | Docker socket/network and Spark image/master are deployment settings; runtime credentials come from an approved secret mechanism. |
| Spark workload | Initialize environment and run smoke write | Idempotently creates the configured namespace, then writes only `sample_spark_job_output` at its dedicated child path; propagates failures. |
| Spark runtime | Execute Python workload in configured job image | Image, master, network, and scaling are managed outside this repository. |

## Interaction Boundaries
- The DAG and workload share the config loader contract; DockerOperator bind-mounts the run-pinned bundle checkout read-only into the Spark container.
- Airflow owns run scheduling, retry, and task status; the Spark job container owns namespace/root initialization and the deterministic smoke write.
- Secret storage and cluster provisioning are outside the repository boundary.
