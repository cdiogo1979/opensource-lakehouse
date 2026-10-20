# Infrastructure Design: `jenkins-deployment`

## Scope and Decisions

- Use one externally managed Airflow 3 deployment with the Git provider installed in the components that process and execute DAG bundles.
- Configure three `GitDagBundle` entries: `lakehouse-dev` tracks the selected feature ref, `lakehouse-uat` tracks `uat`, and `lakehouse-prod` tracks `main`.
- Each bundle checks out the same `dags/`, `configs/`, and `notebooks/` paths from its own branch ref; keep repository root as bundle root.
- Airflow owns Git fetching, branch refresh, DAG parsing, and bundle versioning. Jenkins remains CI for UAT and production but no longer synchronizes files to Airflow.
- Store Git authentication in an Airflow connection or secrets backend. Repository URL, refs, bundle names, and refresh interval are nonsecret platform configuration.

## Component to Infrastructure Mapping

| Component | Infrastructure mapping | Responsibility and boundary |
|---|---|---|
| Git repository | Existing hosted Git repository | Supplies feature, `uat`, and `main` refs; each branch has root-level `dags/`, `configs/`, and `notebooks/` content. |
| `lakehouse-dev` | Airflow 3 GitDagBundle | Tracks the selected feature branch; includes `dags/`, `configs/`, and `notebooks/`; bundle name selects the `dev` config. |
| `lakehouse-uat` | Airflow 3 GitDagBundle | Tracks `uat`; includes `dags/`, `configs/`, and `notebooks/`; bundle name selects the `uat` config. |
| `lakehouse-prod` | Airflow 3 GitDagBundle | Tracks `main`; includes `dags/`, `configs/`, and `notebooks/`; bundle name selects the `prod` config and `main` DAG ID prefix. |
| Git connection | Airflow connection/secrets backend | Supplies private repository credentials outside bundle kwargs; use read-only access and trusted host verification. |
| Branch-selection client | Repository-owned operator CLI plus platform deployment configuration manager | Changes only `lakehouse-dev.tracking_ref`, applies the new config, and triggers the required DAG processor reload/restart. The manager mechanism depends on Airflow hosting and is a platform input. |
| Airflow DAG processor | Existing shared Airflow deployment | Refreshes each branch on its configured interval, parses DAGs, and records bundle versions. |
| Airflow worker/task runner | Existing Airflow execution infrastructure | Must access the versioned bundle checkout for the run and resolve Spark code/config from that checkout. Validate this for the selected executor/deployment topology. |
| Spark job container | Configured Docker image launched by Airflow `DockerOperator` | Runs `spark-submit` with workload/config from the mounted Git bundle checkout and uses the deployment-configured Spark master. Docker host path mapping must preserve the run's bundle version. |
| Jenkins pipeline | Existing Jenkins CI | Runs validation and gates UAT/main; no deployment adapter, Airflow destination settings, or Airflow credential binding. |

## Network and Runtime Inputs

Platform operators provide Airflow 3 version and Git provider compatibility, provider installation, repository URL, UAT/prod refs, the initial dev feature ref, refresh interval, sparse directories, connection ID, secret backend, Git host verification, and network egress from bundle-processing/execution components. They supply the configuration apply/reload command or manager used by the branch-selection client. They also confirm whether the Docker daemon can access and mount the exact bundle-versioned checkout path into the Spark job image or whether run-version-aware immutable staging is required.

## Operational Boundaries

- Bundle refresh visibility is delayed by `refresh_interval`, Git fetch duration, and DAG parse duration.
- Airflow bundle refresh/parse health is monitored in Airflow, separately from Jenkins CI status.
- Airflow's default local DAG bundle must be removed or kept empty/disabled for these DAGs to avoid duplicate/stale definitions.
- Airflow's bundle versioning must remain enabled. The exact setting for reruns should preserve the original run's version unless operators intentionally choose latest-code behavior.
- No deployment transfer locks, atomic SFTP activation, immutable `/opt/jobs` release directory, or automated upload rollback remains in this target topology.
- UAT and production branches may reference distinct commits. The release process determines how a tested UAT commit is promoted to `main`.
- A dev ref change is initiated by the operator client and is not a native Airflow UI operation. The client reports config apply success; Airflow Git fetch and DAG parse readiness are checked separately.

## Infrastructure Inputs Still Required

- Actual Airflow 3 and `apache-airflow-providers-git` versions and component deployment method.
- Git repository URL and branch access policy; exact environment branch names as above.
- Read-only Airflow Git connection and secrets backend configuration; trusted SSH host keys or HTTPS trust policy.
- Deployment-specific method to update the dev bundle configuration and reload/restart required Airflow components; operator authorization and audit logging for branch selection.
- Refresh interval and monitoring for bundle refresh and DAG import failures.
- Executor/task-runner bundle checkout behavior and Spark application file delivery semantics.
- Policy for promoting an accepted UAT commit to `main`, and whether same-commit promotion is desired.
