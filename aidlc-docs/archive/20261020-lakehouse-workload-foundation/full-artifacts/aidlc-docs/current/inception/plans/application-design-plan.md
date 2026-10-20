# Application Design Plan

## Context
- Requirements and execution plan are approved.
- This is a greenfield repository foundation for YAML configuration, exported Python Spark workloads, Airflow DAGs, and Jenkins branch deployment.
- There is no existing application design or component implementation to preserve.

## Design Scope
Define the responsibilities, interfaces, and dependencies for the repository configuration, Spark workload, Airflow orchestration, and Jenkins deployment areas. Keep detailed business rules out of scope because the sample workload is scaffolding only.

## Planned Design Artifacts
- [x] `components.md` — components, purposes, responsibilities, and interfaces.
- [x] `component-methods.md` — high-level function and task signatures, inputs, and outputs.
- [x] `services.md` — orchestration responsibilities and service interactions.
- [x] `component-dependency.md` — dependency matrix and data/configuration flow.
- [x] `application-design.md` — concise consolidation of the design artifacts.
- [x] Validate consistency with approved requirements and execution plan.

## Design Question

### Question 1: Environment Configuration Loading
How should the sample Spark workload obtain values from `configs/<environment>.yml`?

A) The DAG selects the environment file and passes its path to the Spark script; the Spark script loads `storage_path` and `database_name`.

B) Create a shared Python configuration loader used by both the DAG and Spark script.

C) Other (please describe after [Answer]: tag below)

[Answer]: B — use a shared Python configuration loader from both the DAG and Spark workload.

## Execution Checklist
- [x] Read the approved requirements and workflow plan.
- [x] Resolve and record the configuration-loading decision above.
- [x] Generate the five planned application design artifacts.
- [x] Review component boundaries and dependencies for consistency.
- [x] Present the design artifacts for user review and approval.
