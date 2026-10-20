# NFR Requirements Plan: `workload-foundation`

## Context
- Functional Design for `workload-foundation` is approved.
- The `init_environment` job creates the configured namespace idempotently, then overwrites only the dedicated `sample_spark_job_output` table beneath the configured `storage_path`; the table write creates its object prefix.
- Airflow, Spark, and their versions are externally managed; no runtime versions or service targets are known yet.
- Security Baseline is disabled, but approved NFR-1 still forbids checked-in secrets.
- Property-Based Testing is enabled; Python Hypothesis is the planned property-testing framework for the loader properties identified in Functional Design.
- Resiliency Baseline is disabled.

## NFR Category Applicability
- **Scalability**: Not applicable to a tiny synthetic sample workload; no production volume target was specified.
- **Performance**: Not applicable to the starter job; no latency or throughput target was specified.
- **Availability / disaster recovery**: External Airflow and Spark infrastructure is managed outside this repository; no SLO, RTO, or RPO was specified.
- **Security**: Applicable. Preserve secret-free repository artifacts and use external runtime credentials.
- **Reliability**: Applicable. Loader errors fail fast; Spark write failures must propagate to Airflow. The sample write is overwrite mode, so scheduling/trigger behavior matters.
- **Maintainability / testing**: Applicable. Keep shared config contract; enable PBT for loader invariants and use example-based behavior checks for the deterministic sample.
- **Usability / accessibility**: Not applicable; this is repository and orchestration tooling with no user-facing interface.
- **Tech stack**: Python, PySpark, Airflow `DockerOperator`, YAML, Jenkins, and Hypothesis are selected by requirements/design; exact runtime versions remain unknown.

## Questions

### Question 1: Sample DAG Scheduling
The sample job overwrites a table and can target production. How should the DAG be scheduled?

A) Manual trigger only (`schedule=None`); no automatic schedule for this sample.

B) Use an automatic schedule; provide the required cadence and whether the DAG must deploy paused below.

C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2: Runtime Version Constraints
Are the deployed Python, Spark, Airflow, or Airflow Spark provider versions known and required for compatibility?

A) Yes; provide the supported versions below.

B) No; versions are managed externally. Keep repository code compatible with the runtime APIs and avoid pinning external service versions here.

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Assessment Checklist
- [x] Read approved requirements, Application Design, and Functional Design.
- [x] Resolve scheduling and runtime version questions.
- [x] Record applicable scalability, performance, availability, security, reliability, maintainability, and tech stack requirements.
- [x] Select and document Hypothesis for Python property-based testing per PBT-09.
- [x] Create `nfr-requirements.md` and `tech-stack-decisions.md`.
- [x] Present the assessment for approval before NFR Design.
