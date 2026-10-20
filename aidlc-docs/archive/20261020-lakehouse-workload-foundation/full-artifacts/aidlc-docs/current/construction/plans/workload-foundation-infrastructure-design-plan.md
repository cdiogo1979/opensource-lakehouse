# Infrastructure Design Plan: `workload-foundation`

## Context
- Functional Design, NFR Requirements, and NFR Design for `workload-foundation` are approved.
- Airflow and the Docker/Spark runtime are externally managed; Airflow uses `DockerOperator` to launch the Spark job image and `init_environment` initializes the configured namespace before its dedicated smoke write.
- S3 was selected as the storage backend. Exact AWS account/region/bucket/path, Airflow connection IDs, and Spark cluster endpoints were not supplied.

## Infrastructure Category Review
- **Deployment environment**: External Airflow and Spark services are in scope as integration targets; provider/hosting details remain unspecified.
- **Compute**: Spark cluster is externally managed; sizing/scaling is out of scope for this repository. No sizing question is needed without workload targets.
- **Storage**: S3 is selected for `storage_path`; concrete locations, URI scheme, connector, and authorization are platform deployment inputs.
- **Messaging**: Not applicable; the DAG submits directly to Spark and no queue or event broker is required.
- **Networking**: Applicable because DockerOperator requires Docker daemon access and the launched job container must reach the configured Spark master and data services; endpoints and network topology remain deployment inputs.
- **Monitoring**: Use native Airflow task state/logs and external Spark logs for the sample; no separate monitoring service or alerting target was requested.
- **Shared infrastructure**: UAT and production share Airflow and Spark; the selected environment YAML isolates data targets.

## Questions

### Question 1: Environment Infrastructure Isolation
How should UAT and production connect to Airflow and Spark?

A) Separate Airflow deployments and Docker/Spark runtime configurations for UAT and production.

B) Shared Airflow and Spark infrastructure for both environments; isolate data only through the selected YAML configuration.

C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 2: Storage Backend
What storage backend should `storage_path` target?

A) Keep the storage URI provider-agnostic in this repository; the external Spark platform supplies the correct filesystem connector and credentials for each environment.

B) Use a specific backend (S3, ADLS, GCS, HDFS, or other); specify which below.

C) Other (please describe after [Answer]: tag below)

[Answer]: B — S3

## Design Checklist
- [x] Read approved Functional Design and NFR Design.
- [x] Resolve environment infrastructure isolation and storage backend choices.
- [x] Map Airflow, Spark, storage, and secrets to infrastructure boundaries without inventing endpoints.
- [x] Document deployment architecture and runtime prerequisites.
- [x] Generate `infrastructure-design.md` and `deployment-architecture.md` (and shared infrastructure mapping).
- [x] Present Infrastructure Design for approval before Code Generation.
