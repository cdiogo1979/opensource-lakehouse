# Deployment Architecture: `jenkins-deployment`

## Runtime Topology

One Airflow 3 deployment reads the repository using three independently configured Git DAG Bundles. Git is the source of DAG, config, and Spark application artifacts. Jenkins runs CI and branch gates for UAT and production; it does not upload to Airflow.

## Branch-to-Bundle Routing

| Git branch/ref | Airflow bundle | Checked-out directories | DAG environment identity |
|---|---|---|---|
| Operator-selected feature branch | `lakehouse-dev` | `dags/`, `configs/`, `notebooks/` | `dev` |
| `uat` | `lakehouse-uat` | `dags/`, `configs/`, `notebooks/` | `uat` |
| `main` | `lakehouse-prod` | `dags/`, `configs/`, `notebooks/` | `prod` |

Bundle root remains the repository root; `subdir` is unset. Each bundle has an independent stable name and platform-selected refresh interval. The dev bundle's `tracking_ref` is updated by the operator client; UAT and production refs remain fixed. All bundles check out the same directory paths from their selected refs. The shared DAG factory derives environment from bundle name: `lakehouse-main`/`lakehouse-prod` → `prod` config and `main-` IDs; `lakehouse-uat` → `uat`; all other names → `dev`.

## Runtime Sequence

1. An authorized operator selects a feature branch using `airflow_bundle_client.py`. The client validates the ref, updates only the dev bundle configuration, and invokes the deployment-provided config apply/reload operation.
2. The client reports the selected ref and whether configuration apply/reload succeeded. It does not claim the branch's DAGs have parsed.
3. Airflow DAG processor refreshes a bundle from its configured branch using the Airflow Git connection.
4. Airflow parses only the DAG files selected for that environment. Environment-prefixed DAG IDs keep all three bundle contents distinct.
5. When a DAG run starts, Airflow records the bundle's Git commit version.
6. DAG task code resolves the matching config and Spark application from that same run version, then uses `DockerOperator` to launch the configured Spark job image with the bundle checkout bind-mounted read-only.
7. Jenkins CI validates branch changes and gates `uat`/`main`; Airflow fetches accepted changes on its configured refresh schedule.

## Version and Execution Contract

- Bundle versioning remains enabled. Reruns should default to the original bundle version for reproducibility.
- DAG source must not depend on injected `RELEASE_ID`, mutable `/opt/jobs/<environment>` symlinks, or uploaded copies.
- The Docker daemon must be able to bind-mount the run's bundle-versioned checkout into the Spark job container. Verify the source path mapping in the selected deployment; if the daemon cannot access it, add run-version-aware immutable staging before declaring deployment ready.
- Config and helper imports follow the same bundle version and root-relative directory structure.

## Responsibility Boundaries

### Repository-managed

- One root-level DAG definition whose branch version declares a unique environment-prefixed identifier.
- Root `configs/` and `notebooks/` artifacts.
- DAG code that resolves its current bundle version's artifacts and submits Spark work.
- Jenkins CI policy and repository tests; no SFTP publishing adapter.
- `airflow_bundle_client.py`, which updates only the dev tracking ref and delegates deployment-specific config apply/reload to a configured platform backend.

### Platform-managed

- Airflow 3 runtime and Git provider installation/configuration.
- `dag_bundle_config_list`, Git connection, secret backend, network access, host verification, bundle refresh interval, versioning and rerun policy.
- Jenkins branch protection and CI agent configuration.
- Airflow executor/worker access to versioned bundles and Spark application transfer semantics.
- Platform-specific config file/manager, apply command, component restart/reload behavior, and operator authorization for the branch-selection client.
- Spark infrastructure, connection, monitoring, availability, and recovery.

## Security and Reliability

- Airflow Git credentials are external secrets referenced by connection ID; no secret is stored in bundle kwargs or source.
- Git fetch and parse failures appear in Airflow diagnostics. Jenkins reports only CI result and does not claim branch bundle readiness.
- A run remains pinned to the recorded Git commit as it executes; preserve original bundle version when clearing/rerunning unless explicitly changed.
- Refresh timing is eventual and depends on configured interval, fetch, and parse time; no immediate activation guarantee is made.
- Distinct tracking branches do not inherently guarantee identical UAT and production commits. Git promotion policy controls release identity.
