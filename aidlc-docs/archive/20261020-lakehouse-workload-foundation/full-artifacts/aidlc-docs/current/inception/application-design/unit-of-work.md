# Units of Work

## Code Organization Strategy

This repository foundation is organized into two units. Workload code stays at the repository root; Airflow reads the repository through Git DAG Bundles.

```text
configs/
  dev.yml
  uat.yml
  prod.yml
notebooks/
  common/
    config_loader.py
    cli.py
  workload/
    init_environment.py
dags/
  .airflowignore
  dag_defaults.py
  dag_factory.py
  sample_spark_job_dag.py
Jenkinsfile
airflow_bundle_client.py
airflow_bundle_config.example.json
tests/jenkins_deployment/
```

The workload unit owns `configs/`, `notebooks/`, and the environment DAG source. The deployment unit owns the Jenkins CI pipeline, the dev branch-selection client, bundle configuration examples, and deployment guidance. `AGENTS.md` documents both areas.

## Unit 1: `workload-foundation`

- **Purpose**: Establish environment configuration, shared config loading, Spark workload source, and a branch-versioned Airflow DAG.
- **Responsibilities**: Keep one YAML per environment; share the generic config loader and workload CLI; provide the `init_environment` Spark job; centralize standard DAG settings and task creation; derive environment from the bundle name; resolve the DAG, config, helpers, and Spark application from the same Git bundle version.
- **Requirements**: FR-1, FR-2, FR-3, workload/repository portion of FR-5, and NFR-1, NFR-2, NFR-4.
- **Deliverables**: `configs/*.yml`, `notebooks/common/`, `notebooks/workload/init_environment.py`, `dags/.airflowignore`, `dags/dag_defaults.py`, `dags/dag_factory.py`, `dags/init_environment.py`, and workload conventions in `AGENTS.md`.
- **Dependencies**: Uses external Airflow Git connection/provider, Docker daemon, and Spark job runtime supplied by deployment.

## Unit 2: `jenkins-deployment`

- **Purpose**: Run repository CI and provide a controlled CLI for selecting a feature branch for the Airflow development bundle.
- **Responsibilities**: Keep Jenkins CI-only; fix UAT to `uat` and production to `main`; update only the dev bundle tracking ref through a deployment-provided apply/reload command; validate refs, protect the other bundle entries, and document external runtime inputs.
- **Requirements**: FR-4, deployment portion of FR-5, and NFR-1, NFR-3, NFR-4.
- **Deliverables**: CI-only `Jenkinsfile`, `airflow_bundle_client.py`, bundle/client examples, tests under `tests/jenkins_deployment/`, `AIRFLOW_BUNDLES.md`, and updated `AGENTS.md`.
- **Dependencies**: Depends on Unit 1's config, DAG, notebook layout and environment conventions. Airflow config management/reload command is external.

## Execution Order

1. Generate Unit 1 (`workload-foundation`).
2. Generate Unit 2 (`jenkins-deployment`) against Unit 1's finalized paths and bundle contract.
3. Reconcile shared `AGENTS.md` edits so workload and deployment conventions agree.
