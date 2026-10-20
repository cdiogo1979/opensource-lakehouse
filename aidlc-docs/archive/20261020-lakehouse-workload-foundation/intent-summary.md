# Intent Summary: Lakehouse workload foundation and Airflow Git Bundle deployment

## Intent
Lakehouse workload foundation and Airflow Git Bundle deployment (`20261020-lakehouse-workload-foundation`)

## Objective
Establish environment-configured Python Spark workloads and versioned Airflow deployment using Git DAG Bundles, with an operator-controlled development branch selector.

## Date
2026-10-20

## Scope
Includes repository configuration, common Spark CLI and config loading, environment initialization workload, Airflow DAG factory and Git Bundle deployment/client, Jenkins CI, tests, operational documentation, and AI-DLC design records. Excludes Airflow/platform deployment, PR creation, Git push, and live Spark integration.

## Units / workstreams
workload-foundation, jenkins-deployment

## Major requirements
- Provide configs/, notebooks/, and dags/ as the workload foundation.
- Keep one YAML per dev/uat/prod environment with required storage_path and database_name, while allowing arbitrary nested application settings.
- Run Python Spark workloads from Airflow with config and code pinned to the same Git revision.
- Support trusted feature-branch testing for the development Git DAG Bundle.
- Keep Jenkins as compile and unit-test CI without copying files into Airflow.

## Architecture and design decisions
- Airflow 3 Git DAG Bundles fetch the repository root and use stable bundle names to select runtime environment configuration and DAG ID prefix.
- Bundle mapping: lakehouse-main/lakehouse-prod -> prod.yml and main-; lakehouse-uat -> uat.yml and uat-; all other bundle names -> dev.yml and dev-.
- Airflow uses a common DAG factory and DockerOperator to execute spark-submit; each DAG declaration supplies its workload entrypoint and schedule.
- Environment identity is derived in Airflow from bundle identity, so a shared branch does not require a branch-specific marker file.
- Secrets and runtime credentials are external to repository YAML and deployment examples.

## Implementation decisions
- The generic config loader validates required current workload keys and provides arbitrary nested YAML data; common CLI parsing is in notebooks/common/cli.py.
- init_environment creates the configured namespace if absent, then overwrites only the dedicated two-row synthetic sample_spark_job_output table.
- The table write creates the object-storage prefix; the workload does not use Hadoop S3A solely to create a directory marker.
- The operator client validates feature refs and changes only lakehouse-dev tracking_ref, invoking a deployment-owned apply/reload command.
- Jenkins compiles the Python client, DAGs, and workloads and runs pytest; it does not publish files or mutate Airflow bundle refs.

## Deviations
- Verification waiver accepted by user with the remaining Flake8/Bandit findings and unverified live Airflow/Spark integrations listed above.
- The local Airflow deployment observed during troubleshooting used lakehouse-main, while the example three-bundle configuration uses lakehouse-prod for the main branch; deployment owners must reconcile this platform-specific naming.
- No PR, push, or platform deployment was performed.

## Verification
User-approved verification waiver. Compile validation, 48 unit/property tests, Ruff, and Black passed. Flake8 still reports two E203 warnings; Bandit reports 67 low-severity findings. Live confirmation that the .airflowignore fix parses in Airflow and Spark/Nessie/object-storage integration were not completed. These are limitations, not passed checks.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/jenkins-deployment.md

## Superseded decisions
- Environment-specific dags/dev, dags/uat, and dags/prod folder layouts and a branch-specific .lakehouse-environment marker were superseded by one root dags/ layout with environment identity derived from the Airflow bundle name.
- Jenkins/SFTP file-copy publication and a direct deployment adapter were superseded by Airflow Git DAG Bundles; the client only selects a development bundle ref.
- A Spark sample output job evolved into init_environment, which initializes the namespace and writes one dedicated synthetic smoke table.
- Direct Hadoop S3A prefix creation was removed; the table write creates the object keys/prefix.
- Parsing standard CLI arguments inside config_loader.py was superseded by a shared CLI module so config loading remains reusable.

## Archived artifacts
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/aidlc-docs/current/compaction/20261020-lakehouse-workload-foundation/manifest.json
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/README.md
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/AGENTS.md
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/AIRFLOW_BUNDLES.md
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/Jenkinsfile
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/airflow_bundle_client.py
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/airflow_bundle_client.example.yml
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/airflow_bundle_config.example.json
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/configs
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/dags
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/notebooks
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/scripts
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/tests
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/requirements-dev.txt
- aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/pyproject.toml

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261020-lakehouse-workload-foundation/full-artifacts/`
