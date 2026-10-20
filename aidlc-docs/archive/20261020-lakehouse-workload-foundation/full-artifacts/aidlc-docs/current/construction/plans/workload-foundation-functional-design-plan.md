# Functional Design Plan: `workload-foundation`

## Context
- Requirements, revised execution plan, Application Design, and two-unit decomposition are approved.
- Unit of Work 1 is `workload-foundation`; its definition is in `inception/application-design/unit-of-work.md`.
- No user stories were generated; approved requirements and the workload unit define the scope.
- Canonical functional design path in the approved knowledge inventory: `aidlc-docs/knowledge/opensource-lakehouse/functional-design/configuration-loader.md`.

## Design Scope
Specify the environment YAML contract, shared loader behavior, Spark script input behavior, and DAG-to-Spark configuration flow. The sample has no business domain or data transformation specified; do not invent one.

## Planned Artifacts
- [x] `business-logic-model.md` — configuration and execution flow for this unit.
- [x] `business-rules.md` — environment, required key, and validation rules.
- [x] `domain-entities.md` — configuration value model and explicit absence of business-domain entities.
- [x] Identify testable properties for PBT-01, or state with rationale that none exist.
- [x] Reconcile all design choices with requirements and Application Design.

## Questions

### Question 1: Configuration Validation Failures
How should the shared loader handle unsupported environments, missing YAML files, invalid YAML, or missing required keys?

A) Fail immediately with a clear error identifying the environment/file/key problem; do not silently default values.

B) Use defaults or warnings for missing/invalid values where possible.

C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2: Sample Spark Workload Side Effects
What should the starter Spark script do with the configured `storage_path` and `database_name`?

A) Demonstrate config loading and Spark startup only; log the selected non-secret settings and perform no data writes.

B) Create and write a small sample dataset using the configured targets.

C) Other (please describe after [Answer]: tag below)

[Answer]: B

### Clarification Question 3: Sample Data Output
The sample will write data using environment-specific targets, which could include production. What output behavior should the starter job use?

A) Write a tiny synthetic dataset to a dedicated `sample_spark_job_output` table in `database_name` and `storage_path`, using overwrite mode so reruns are repeatable.

B) Append a tiny synthetic dataset to a dedicated `sample_spark_job_output` table in `database_name` and `storage_path`.

C) Write Parquet files under a dedicated sample subdirectory of `storage_path`; do not register a database table.

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Execution Checklist
- [x] Read unit, requirements, application design, and canonical knowledge inventory.
- [x] Resolve the sample workload output behavior.
- [x] Create the three planned functional design artifacts.
- [x] Check PBT-01 properties and document the result.
- [x] Present functional design artifacts for approval before NFR Requirements.

## Initialization Change Addendum (2026-10-20)

The approved requirements amendment changes this unit's sample workload into `init_environment`. It must create the configured namespace idempotently, avoid separate S3A storage-root creation, preserve unrelated storage contents, and retain the overwrite of only the dedicated `sample_spark_job_output` smoke table.

### Design Updates
- [x] Update `business-rules.md` with namespace/root initialization, idempotence, failure handling, and safe smoke-write scope.
- [x] Update `business-logic-model.md` with ordered initialization and smoke-write flow.
- [x] Update `domain-entities.md` to describe initialization targets and the smoke-record role.
- [x] Identify PBT-01 properties for idempotence, target scope, ordering, and preserved smoke output.
- [x] Reconcile the updates with the approved requirements and workflow addendum.

The canonical workload functional-design document remains planned in the approved knowledge inventory and will be consolidated at intent closure; this stage updates the active design artifacts used for implementation.

### Shared DAG Factory Refinement
- [x] Record the branch environment marker and thin DAG declaration contract in `business-rules.md`.
- [x] Centralize DAG configuration and standard validation/Spark task construction in `dags/dag_factory.py` and shared arguments in `dags/dag_defaults.py`.
