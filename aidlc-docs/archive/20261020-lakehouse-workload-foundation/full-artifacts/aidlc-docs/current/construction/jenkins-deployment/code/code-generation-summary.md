# Code Generation Summary: `jenkins-deployment`

## Generated and Updated Files

- `dags/init_environment.py`, `dags/.airflowignore`, `dags/dag_defaults.py`, and `dags/dag_factory.py` — One thin DAG declaration selected from each bundle's Git ref. The bundle name selects the environment; the declaration supplies only the Python entrypoint and schedule; the factory builds common tasks/settings and resolves the matching bundle config and workload.
- `airflow_bundle_config.example.json` — Secret-free three-bundle example. Dev uses a replaceable feature ref; UAT uses `uat`; production uses `main`.
- `airflow_bundle_client.py` — `show` and `select --branch` CLI operations. Validates Git branch format, a required configured feature-ref prefix, and protected refs; updates only `lakehouse-dev`; writes atomically; invokes an argv-only apply command; and restores the old config if apply fails.
- `airflow_bundle_client.example.yml` — Non-secret client settings shape with an external config path and platform apply-command placeholder.
- `AIRFLOW_BUNDLES.md` — Airflow/provider setup, client use, trusted-operator boundary, ref application, refresh/parse readiness, and Spark path verification.
- `Jenkinsfile` — Repository syntax and unit-test CI only; it no longer publishes Airflow artifacts.
- `tests/jenkins_deployment/test_airflow_bundle_client.py` — pytest/Hypothesis tests for bundle config validation, dev-only ref updates, protected/invalid refs, apply command arguments, and rollback behavior.
- `AGENTS.md` — Updated repository layout, bundle versioning, client, and workload conventions.
- `requirements-dev.txt` — Continues to provide PyYAML, pytest, and Hypothesis. Removed the SFTP-only `requirements-deploy.txt`.

## Retired SFTP Deployment Files

- Removed `airflow_deployment_adapter.py`, `jenkins_deployment.py`, `requirements-deploy.txt`, `tests/jenkins_deployment/test_policy.py`, and `tests/jenkins_deployment/test_sftp_adapter.py`.
- Removed Jenkins target JSON/credential/lock/upload behavior. Jenkins is CI only.
- Removed environment-folder DAG copies. All bundles use the same root DAG source and helper files, with the bundle name carrying environment identity.

## Deployment Contract

1. The Airflow deployment configures `lakehouse-dev`, `lakehouse-uat`, and `lakehouse-prod` as versioned `GitDagBundle` entries.
2. The deployment client edits only the dev bundle `tracking_ref`; refs `dev`, `uat`, and `main` are rejected. UAT and production stay fixed on `uat` and `main`.
3. The client reads a deployment-owned JSON bundle config and YAML settings file. The settings identify an apply command as an argument list; the command is passed without a shell and must update Airflow's effective `dag_bundle_config_list` and reload/restart the required components.
4. Client success means the apply command completed successfully. Operators must separately confirm the new branch was fetched and parsed in Airflow.
5. Each DAG run uses the Git bundle commit version recorded by Airflow. The shared factory derives the repository root from its bundle path, mounts sibling `configs/` and `notebooks/` paths read-only into the Docker job container, and uses deployment-configured image, Docker endpoint, network, and Spark master settings.
6. Git credentials stay in the Airflow Git connection or secrets backend. Feature branches execute with Airflow privileges; restrict client access to trusted operators.

## Requirement Traceability

- **FR-4**: Git DAG Bundles replace artifact upload. The operator CLI selects the dev feature ref, and UAT/prod remain fixed to `uat`/`main`.
- **FR-5**: `AGENTS.md` and `AIRFLOW_BUNDLES.md` document the repository and operational contract.
- **NFR-1 / NFR-3**: Git credentials remain external; invalid refs and apply failures produce safe errors and rollback behavior.
- **Version consistency**: DAG runs preserve their Airflow-recorded Git bundle version; config and Spark source paths are derived from that checkout.
- **PBT-01/PBT-09**: Tests cover protected refs, dev-only changes, bundle integrity, and failure rollback.

## Platform Inputs and Verification Boundary

The platform owner supplies Airflow/provider versions, repository URL, Git connection, refresh interval, bundle config deployment path, operator settings path, a trusted argv-style apply/reload command, and permissions for operators. The client does not include a Docker Compose or Kubernetes controller; the configured command is the deployment-specific adapter.

Tests and live Airflow integration were not executed during Code Generation. Build and Test must verify client behavior, DAG imports, bundle parsing and version pinning, the actual config apply/reload operation, Docker daemon visibility of the run-versioned checkout, and the image's access to matching application/config paths. If run-versioned paths are unavailable to the Docker daemon, revise the plan and implement immutable commit-addressed staging.
