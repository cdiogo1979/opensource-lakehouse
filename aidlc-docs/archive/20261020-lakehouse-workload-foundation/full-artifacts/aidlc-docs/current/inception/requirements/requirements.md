# Requirements: Airflow and Spark Repository Foundation

## Intent Analysis
- **User request**: Start the AI-DLC process for `opensource-lakehouse` and establish environment configuration, Python Spark code, and Airflow DAG locations.
- **Request type**: New feature / repository foundation.
- **Project type**: Greenfield.
- **Scope estimate**: Multiple repository artifacts: configuration structure, sample Spark script, Airflow DAG, Jenkins pipeline, and repository guidance.
- **Complexity estimate**: Moderate because branch-based deployment spans repository conventions, Jenkins, Airflow, and a separately managed Spark cluster.

## User and Business Goal
Provide a consistent repository layout for Python Spark workloads and Airflow orchestration, with environment-specific configuration. A single Airflow 3 deployment reads environment-scoped Git DAG Bundles from the `dev`, `uat`, and `main` branches; Jenkins remains the CI gate for UAT and production branch changes.

## Functional Requirements

### FR-1: Environment Configuration
- Create one YAML file per environment directly under `configs/`: `configs/dev.yml`, `configs/uat.yml`, and `configs/prod.yml`.
- Each environment file must define `storage_path` and `database_name`.
- Keep the configuration in these three files; separate environment folders are not required.
- Keep environment-dependent values, including `storage_path` and `database_name`, out of shared Spark code and DAG logic where practical; load them from the selected environment file.
- The shared loader must preserve arbitrary additional top-level keys and nested YAML settings without requiring loader schema changes; applications can read them through a generic mapping interface. `storage_path` and `database_name` remain required for the current Spark workload.
- Do not commit credentials, tokens, or other secrets. Runtime credentials and deployment settings must be supplied through Jenkins/Airflow configuration or an approved secret store.

### FR-2: Spark Workload Source
- Create a `notebooks/` location for Python Spark code exported from Jupyter notebooks as `.py` files.
- Include an `init_environment` Spark script that can be submitted to the configured Spark runtime, initializes configured resources idempotently, and retains the deterministic sample-table write as a smoke test.
- Keep environment configuration external to the script.

### FR-3: Airflow DAGs
- Create a `dags/` location for Airflow DAG definitions.
- Include a manual DAG using `DockerOperator` to launch the configured Spark job image and run `spark-submit` for the `init_environment` workload.
- Keep each DAG declaration limited to its Python entrypoint filename and schedule; use shared factory code for common DAG settings and task construction.
- Refer to repository artifacts that exist and pass environment-specific settings without embedding secrets.

### FR-4: Airflow Git DAG Bundles
- Configure one Airflow 3 deployment with three named Git DAG Bundles: `lakehouse-dev` tracks an operator-selected feature branch; `lakehouse-uat` tracks `uat`; and `lakehouse-prod` tracks `main`.
- Provide a repository-owned deployment client that lets an authorized operator change only the `lakehouse-dev` bundle's tracking ref to a selected feature branch, applies the Airflow bundle configuration change, and invokes the deployment-specific command that applies the config and any required DAG processor reload/restart.
- The client must leave UAT and production refs unchanged, reject protected/non-feature refs and malformed branch names, and report the selected ref and apply outcome without exposing secrets.
- Keep Airflow's DAG processor responsible for polling the configured branches. `refresh_interval` is an Airflow setting; branch changes become visible after a refresh and successful DAG parsing.
- Keep one `dags/` folder. Each Git bundle checks out that same path from its configured ref; the bundle name selects the environment and DAG ID prefix (`lakehouse-main`/`lakehouse-prod` → `prod` config and `main-` IDs, `lakehouse-uat` → `uat`, all others → `dev`). The selected feature branch must provide the DAG factory, config, and workload from that branch's commit.
- DAG IDs and submitted Spark job names must be environment-prefixed and unique across all three bundles.
- Store private Git access in an Airflow Git connection or approved secrets backend. Bundle configuration may contain repository URL, branch, bundle name, and refresh settings, but no credential values.
- Airflow must retain bundle versioning so each DAG run uses the Git commit version that defined it. Do not inject a deployment release marker into DAG source.
- Jenkins remains the branch CI gate. Jenkins does not copy files to Airflow, invoke an upload adapter, or manage Airflow Git credentials. No manual SFTP publisher is part of the updated deployment contract.
- The dev branch-selection client is a separately invoked operator tool, not a public Airflow DAG or a Jenkins automatic deployment. It must use the deployment's supported configuration/apply mechanism; Airflow's native UI is not assumed to edit bundle tracking refs.
- The DAG factory and Spark application must resolve matching config and code from the bundle version used by that run. The code-generation plan must verify bundle checkout access from the task execution environment and the Spark submission path behavior before implementation is accepted.

### FR-5: Repository Guidance
- Update `AGENTS.md` so repository conventions describe the Airflow/Spark/Jenkins layout and no longer prescribe Databricks jobs as the authoritative orchestrator for this project.
- Document the purpose of each top-level artifact location and the environment-to-branch mapping.

## Non-Functional Requirements
- **NFR-1: Secret handling**: No secret values may appear in source, YAML examples, DAGs, Jenkins pipeline files, or documentation. Use named runtime references/placeholders and external secret configuration.
- **NFR-2: Maintainability**: Shared code must be reusable across environments; environment differences belong in the corresponding `configs/<environment>.yml` file.
- **NFR-3: Operational clarity**: The branch-selection client must show which development branch is selected and fail clearly when branch validation, configuration update, or Airflow reload fails.
- **NFR-4: Verification**: Validate YAML, Python, bundle configuration, client behavior, and referenced DAG/script paths in the AIDLC Build and Test stage.
- **NFR-5: Idempotent initialization**: Repeated initialization runs must accept an existing namespace and storage prefix without deleting unrelated objects or tables.

## User Scenarios
1. A developer adds or exports a Python Spark workload under `notebooks/` and supplies environment-specific values in the matching `configs/<environment>.yml` file.
2. Airflow loads the environment DAG from its Git bundle; the DAG uses `DockerOperator` to launch the configured Spark job image and execute the matching workload with `spark-submit`.
3. An operator runs the branch-selection client with a feature branch name; it updates only `lakehouse-dev`, applies/reloads Airflow, and reports the selected ref and outcome.
4. The development bundle fetches and parses the selected feature branch, and a dev DAG run uses config and Spark code from the same recorded commit.
5. UAT and production continue tracking `uat` and `main`; Jenkins validates and gates those branches without transferring artifacts.
6. The dev bundle `lakehouse-dev` tracks the feature branch selected by the deployment client; UAT remains on `uat` and production remains on `main`.
7. Each bundle checks out the same `dags/`, `configs/`, and `notebooks/` paths from its own Git ref; the bundle name supplies environment identity and the branch version supplies matching code/configuration.
8. DAG runs record and use their Git bundle commit version, including for reruns when configured to preserve the original version. New commits on the selected branch are picked up on the next bundle refresh and parse cycle; switching the selected branch applies through the client.

## Acceptance Criteria
- [ ] `configs/dev.yml`, `configs/uat.yml`, and `configs/prod.yml` each define `storage_path` and `database_name`, with no secret values.
- [ ] Additional environment-specific YAML keys and nested mappings are preserved by the loader and accessible to applications without changing the loader.
- [ ] `notebooks/` contains the exported `init_environment` Python Spark script.
- [ ] The initialization script creates the configured Nessie namespace if absent, then writes only the dedicated `sample_spark_job_output` smoke-test table beneath the configured path; the table write creates its object prefix.
- [ ] Environment-scoped DAGs use `DockerOperator`, referencing the initialization script and matching environment config from the same bundle version.
- [ ] The bundle name selects its config environment and DAG ID prefix; the DAG declaration passes only the Spark entrypoint filename and schedule, and a shared factory supplies the common DAG settings, config-validation task, and Spark submission task.
- [ ] Airflow is configured with separate `GitDagBundle` entries: the dev bundle uses a client-controlled tracking ref, UAT uses `uat`, and production uses `main`; bundle names and environment DAG IDs are unique.
- [ ] The deployment client changes only the dev bundle ref, accepts only configured feature-ref prefixes, rejects reserved and malformed refs, applies the configuration safely, and invokes the target's supported configuration/apply operation.
- [ ] Git credentials are referenced through an Airflow connection/secrets backend and do not appear in bundle kwargs or repository files.
- [ ] `AGENTS.md` describes the adopted structure and branch mapping consistently.
- [ ] YAML, Jenkins pipeline, and referenced artifact paths are validated in the later Build and Test stage.
- [ ] Every environment DAG resolves config and Spark source from the same bundle checkout/version as the DAG run; task-runner and Spark-submit file visibility are verified for a selected feature branch.
- [ ] Jenkins no longer publishes DAGs/workloads or requires deployment SFTP credentials, target configuration, deployment locks, or adapter selection.

## Decisions and Constraints
- Airflow is the orchestrator; this is a separate project from the Databricks conventions currently in the repository guide.
- Airflow uses `DockerOperator` to launch a Spark job container; that container runs `spark-submit` with a deployment-configured Spark master.
- Environment configuration format is YAML.
- CI/CD is implemented with a Jenkins pipeline.
- Airflow bundle mapping is `lakehouse-dev` → operator-selected feature branch, `lakehouse-uat` → `uat`, and `lakehouse-prod` → `main`. Jenkins CI gates UAT and production branches but does not publish artifacts.
- Airflow version must support DAG Bundles and the Git provider bundle implementation; Airflow 3 is required by this design. Pin actual version/provider compatibility when the platform version is selected.
- The Airflow platform must configure the Git repository URL, per-bundle tracking refs, refresh interval, provider package, Git connection/secrets backend, and repository network access.
- Airflow's native UI does not provide a tracking-ref selector. The client updates the deployment-managed bundle configuration and uses a platform-specific reload/restart operation. That mechanism must be selected for the actual Airflow deployment.
- Exact promotion policy for moving a tested UAT commit to production remains a platform/release-management choice. Branch tracking means each branch may point at a different commit; no same-SHA promotion guarantee is assumed.
- Security Baseline extension: disabled by user choice. The project's explicit no-secrets rule remains in force.
- Property-Based Testing extension: enabled by user choice. The initialization enhancement has an idempotence property; cover repeated initialization behavior with property-based tests alongside example-based safety checks.
- Resiliency Baseline extension: disabled by user choice.

## Change Request: Idempotent Environment Initialization
- **User request**: "is it possible to adjust the sample_spark_job and chnage it to init_environment job so that the databases and data paths are initialised if they dont exist?"
- **Clarification answer**: Option B (user replied `2`) — initialize namespace and storage prefix, then retain the existing sample table write as a smoke test.
- **Behavior**: Rename the exported Spark workload and DAG/job-facing names to `init_environment`; create the configured Nessie namespace if absent; then overwrite only the deterministic `sample_spark_job_output` table at its dedicated child path. The table write creates the object prefix; do not call Hadoop S3A filesystem APIs to create a directory marker.
- **Idempotence and safety**: Existing namespace/prefix must be accepted. Initialization must not remove unrelated objects or tables. The smoke test may overwrite only its dedicated table and child path.
- **Storage semantics**: Do not separately initialize the object-store prefix through Hadoop filesystem APIs. The table write creates the needed object keys.

## Change Request: Shared DAG Factory
- **User request**: Simplify DAG declarations so they specify only the Python job/task entrypoint filename and schedule; standard DAG creation and task settings are shared.
- **Clarification**: Derive environment identity from the Airflow bundle name so all Git refs can keep the same DAG source while creating unique prefixed DAG IDs and loading matching configs.
- **Behavior**: A shared factory reads the bundle identity from the versioned checkout path, derives the workload and task names from the entrypoint filename, validates the matching environment config, creates the standard DockerOperator Spark submission task, and applies common Airflow settings. The DAG source passes only `entrypoint_file` and `schedule`.
