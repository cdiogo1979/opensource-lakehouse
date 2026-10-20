# Code Generation Plan: `workload-foundation`

## Plan Status

Part 1 — Approved. Part 2 — Generation is complete and approved; the user requested generic YAML key support, shared workload argument parsing, and simplified output path construction, all implemented. This plan remains the single source of truth for Unit 1 code generation.

## Unit Context

- **Project type**: Greenfield; workspace root is `/Users/carlosdiogo/code_repo/opensource-lakehouse`.
- **Unit purpose**: Establish environment configuration, a shared config loader, sample Spark workload, and Airflow orchestration.
- **Requirements**: FR-1, FR-2, FR-3, workload/repository-layout portion of FR-5, NFR-1, NFR-2, and NFR-4.
- **Stories**: User Stories stage was skipped. Trace implementation to FR-1/AC, FR-2/AC, FR-3/AC, and FR-5/AC in `inception/application-design/unit-of-work-story-map.md`.
- **Dependencies**: No repository unit dependencies. Runtime depends on externally managed Airflow, Spark, S3 access, and catalog/database prerequisites.
- **Interfaces**: `EnvironmentConfig` carries the selected environment and exposes the complete YAML mapping; required workload settings are accessed by key, and arbitrary top-level/nested settings remain available. The same strict loader is used by the DAG and Spark workload. The environment-scoped DAG derives its environment from its bundle directory and launches the matching workload through `DockerOperator` and `spark-submit`.
- **Entities**: No business-domain entities. `EnvironmentConfig` is a technical value object; `SampleRecord` is a tiny deterministic synthetic example.
- **Infrastructure decisions**: UAT and production share Airflow and the Docker/Spark runtime; their data targets are selected through YAML. S3 is the storage backend. No AWS locations, catalog product, Docker daemon endpoint, image, Spark master, or runtime versions were supplied.

## Code Location

Application files belong at the repository root, never under `aidlc-docs/`. Follow the approved layout:

```text
configs/dev.yml
configs/uat.yml
configs/prod.yml
notebooks/common/config_loader.py
notebooks/common/cli.py
notebooks/workload/sample_spark_job.py
dags/init_environment.py
dags/dag_defaults.py
tests/workload_foundation/...
AGENTS.md
```

The YAML examples will contain obvious, non-secret replacement values for S3 locations and database names because concrete deployment locations were not provided. They must be syntactically valid and must not imply that the placeholders are deployable targets. Replace them with approved environment values before execution.

## Generation Steps

1. [x] **Confirm generation inputs and PBT scope** — Re-read approved Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Unit 1 story map, and dependency map. Confirmed this unit owns environment selection/validation and the deterministic bounded sample write; the PBT suite will cover loader invariants and the overwrite contract with generated environment values.
2. [x] **Create environment configuration** — Add `configs/dev.yml`, `configs/uat.yml`, and `configs/prod.yml`, each containing non-empty `storage_path` and `database_name`, no secrets, and clearly marked replaceable S3/database example values. Keep the three files directly in `configs/`.
3. [x] **Implement shared config loader** — Add `notebooks/common/config_loader.py` with an immutable `EnvironmentConfig` mapping and one loading/validation function. Accept only `dev`, `uat`, or `prod`; resolve only the matching YAML; require non-empty string `storage_path` and `database_name`; preserve arbitrary additional YAML settings and nested values; reject missing files, malformed YAML, non-mapping roots, or invalid required values; never fall back to defaults or another environment.
4. [x] **Implement deterministic Spark sample** — Add `notebooks/workload/sample_spark_job.py` as a Python Spark script suitable for export from Jupyter. Require the supported environment passed by the deployed DAG, load configuration through the shared loader, create a tiny fixed synthetic dataset, and overwrite only `database_name.sample_spark_job_output` at a dedicated child path under `storage_path`. Propagate failures; do not write to the root or unrelated locations, and do not include credentials.
5. [x] **Implement environment-scoped Airflow DAG** — The user later requested that the sample use the Docker submitter from the separate Airflow/Spark test setup. All three bundle-scoped DAGs now use `DockerOperator` to run `spark-submit` in the configured job image, with the matching bundle checkout mounted read-only. Image, Docker daemon, network, and Spark master are external settings.
6. [x] **Add property and example tests and dev dependencies** — Add Hypothesis property tests for loader environment isolation, valid required values, generated invalid-value rejection, no-fallback behavior, preservation of arbitrary nested YAML values, safe child-path derivation, and the deterministic overwrite contract, plus example-based tests for unsupported environment, missing file, malformed/non-mapping YAML, missing/empty/wrong-type keys, and the sample's fixed schema/rows. Add Hypothesis, pytest, and PyYAML to `requirements-dev.txt`. Keep external Spark/Airflow integration tests out of local tests; capture their prerequisites in later Build and Test instructions. Never use real data or credentials.
7. [x] **Complete Unit 1 repository guidance** — Update `AGENTS.md` to document `configs/`, `notebooks/common/`, `notebooks/workload/`, `dags/`, Jupyter export expectations, explicit environment selection, S3/database placeholders, secret handling, and the manual Airflow-to-Spark flow. State that Jenkins deployment and branch mapping are owned by Unit 2 and will be added/reconciled there.
8. [x] **Write Unit 1 code-generation summary** — Create `aidlc-docs/current/construction/workload-foundation/code/code-generation-summary.md` listing generated files, configuration replacement inputs, runtime assumptions, requirements/story traceability, and outstanding external prerequisites. Documentation only; no infrastructure deployment.
9. [x] **Generalize YAML settings access** — Per the user's Code Generation review request, make `EnvironmentConfig` expose the complete YAML mapping, preserve arbitrary additional top-level/nested settings, retain validation of required `storage_path` and `database_name`, update consumers and example/property coverage, and synchronize requirements/design/repository guidance. Traces to FR-1 and NFR-2.
10. [x] **Share workload CLI parsing** — Per the user's review request, move common `--environment` and `--config-dir` parsing into `notebooks/common/cli.py`, import it from the sample workload, distribute it to the Spark container, and document the shared convention. Keep `config_loader.py` focused on configuration loading.
11. [x] **Simplify sample output path construction** — Per the user's review request, remove `build_sample_output_path`, assume `storage_path` ends in `/` and `sample_spark_job_output` is clean, append the table name directly, update sample configs and existing path references, and document the assumption.
12. [x] **Align bundle-specific DAG identity** — Use one root-level `dags/` directory; the bundle name supplies environment identity (`lakehouse-main`/`lakehouse-prod` → `main` prefix and `prod` config; `lakehouse-uat` → `uat`; all others → `dev`). The shared factory resolves config/workload from the same versioned bundle checkout. `.airflowignore` excludes helper modules from DAG discovery.

## Plan Preparation Checklist

- [x] Read approved unit design artifacts and story/dependency map.
- [x] Confirm project type, workspace root, and code location rules.
- [x] Define exact paths, interfaces, dependencies, entities, and requirement traceability.
- [x] Sequence generation as executable numbered steps with completion checkboxes.
- [x] Obtain user approval before generating application files.

## Scope Boundaries

- Unit 1 does not create the root `Jenkinsfile` or finalize branch deployment instructions; those belong to `jenkins-deployment` after Unit 1 is complete.
- Unit 1 does not provision Airflow, Spark, AWS/S3, catalog/database, IAM, network, or external connections.
- Build and Test is a later AIDLC stage. No local tests or external integration runs occur as part of this plan approval.

## Initialization Change Addendum (2026-10-20)

The approved requirements and functional design change the sample workload into an `init_environment` job. This addendum is the code-generation record for that approved change.

### Generation Checklist
- [x] Replace `notebooks/workload/sample_spark_job.py` with `notebooks/workload/init_environment.py`.
- [x] Create the configured namespace using `CREATE NAMESPACE IF NOT EXISTS`.
- [x] Avoid Hadoop S3A filesystem directory creation; the dedicated table write creates the object prefix, preserving unrelated objects.
- [x] Run the deterministic overwrite smoke write only after namespace and root initialization succeeds, scoped to `sample_spark_job_output`.
- [x] Update the one root DAG's job, task, container, and DAG identifiers and Spark script reference to `init_environment` while retaining branch-provided environment identity.
- [x] Add example coverage for the namespace statement and smoke output scope.
- [x] Add Hypothesis coverage for repeat initialization, existing/missing roots, namespace state, and preservation of unrelated storage state.
- [x] Synchronize active repository guidance, architecture, NFR/design artifacts, and code-generation summary.
- [x] Implement the thin-DAG refinement: each DAG supplies only `entrypoint_file` and `schedule`; `dags/dag_factory.py` derives the environment from the Airflow bundle checkout path and creates the standard DAG/tasks.
- [x] Record generated code and tests; do not execute tests until the Build and Test stage.

### Implementation Notes
- The storage prefix is not separately initialized through Hadoop filesystem APIs; the output table write creates it.
- Catalog, filesystem, and smoke-write errors propagate to the Airflow task. The smoke write is not attempted if initialization fails.
- Tests are authored but not run during Code Generation. Live Nessie, S3-compatible storage, Airflow, and Docker integration remain unverified.
