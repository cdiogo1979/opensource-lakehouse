# Requirement-to-Unit Map

The User Stories stage was skipped because this is developer tooling and repository infrastructure work. Each approved requirement and acceptance item is mapped below instead.

| Requirement / acceptance item | Owning unit | Notes |
|---|---|---|
| FR-1 / AC: three environment YAML files with required `storage_path` and `database_name`, plus arbitrary preserved YAML settings | `workload-foundation` | Shared generic mapping contract; loader schema changes are unnecessary for additional app settings. |
| FR-2 / AC: exported Python Spark sample | `workload-foundation` | Run with `spark-submit` in the Docker job image using a configured Spark master. |
| FR-3 / AC: DAG using `DockerOperator` | `workload-foundation` | One DAG folder is read from each selected branch; a branch-specific marker supplies environment identity, and the shared factory launches the Spark job image and resolves workload/config paths from the run-pinned Git bundle. |
| FR-4 / AC: Git bundle delivery and dev ref selection | `jenkins-deployment` | `lakehouse-dev` tracks an operator-selected feature branch; UAT tracks `uat`; production tracks `main`. The client applies only the dev ref change. |
| FR-5 / AC: update `AGENTS.md` | `workload-foundation`, `jenkins-deployment` | Unit 1 documents layout; Unit 2 documents pipeline and branch rules; reconcile in Unit 2. |
| NFR-1: secret handling | Both | Examples contain no secrets; Jenkins/Airflow use external credentials. |
| NFR-2: maintainable shared configuration | `workload-foundation` | One loader contract and one YAML file per environment. |
| NFR-3: operational clarity and client apply status | `jenkins-deployment` | Validate feature refs before configuration update; separate apply success from Airflow parse readiness. |
| NFR-4: configuration, pipeline, and path verification | Both | Unit 1 verifies YAML and DAG/script linkage; Unit 2 verifies CI syntax, client behavior, bundle mappings, and integration prerequisites. |
