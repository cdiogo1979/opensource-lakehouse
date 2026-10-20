# NFR Design Plan: `workload-foundation`

## Context
- NFR Requirements for `workload-foundation` are approved.
- The sample DAG is manual-trigger only and writes a deterministic dataset by overwriting one dedicated sample table.
- Secrets and runtime targets are externally configured; runtime versions are not pinned.

## Category Applicability
- **Resilience patterns**: Applicable for Spark write failures and retries. Clarify whether a task retries automatically or requires manual recovery.
- **Scalability patterns**: Not applicable to environment initialization and a tiny deterministic smoke dataset; no throughput/growth requirement exists.
- **Performance patterns**: Not applicable; no latency/throughput target exists.
- **Security patterns**: Applicable. Use Airflow Connections/Variables or a secret backend for runtime credentials; never serialize secrets in DAG params or logs. Environment values are explicitly selected and validated.
- **Logical components**: Airflow uses DockerOperator, a Docker daemon, and a configured Spark job image; spark-submit runs against a deployment-configured Spark master.

## Question

### Question 1: Spark Task Retry Behavior
The write targets a dedicated table in overwrite mode and is repeatable, but a retry will repeat that write. What should the sample DAG do after a Spark task failure?

A) No automatic retries (`retries=0`); an operator reviews the failure before manually rerunning.

B) Retry once automatically; the deterministic overwrite of the dedicated table is considered safe to repeat.

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Design Checklist
- [x] Read the approved NFR Requirements and Functional Design.
- [x] Resolve retry behavior.
- [x] Define secret handling and explicit environment selection patterns.
- [x] Define safe write isolation and failure propagation patterns.
- [x] Document N/A scalability/performance and absence of new infrastructure components.
- [x] Generate `nfr-design-patterns.md` and `logical-components.md`.
- [x] Present NFR Design for approval before Infrastructure Design.
