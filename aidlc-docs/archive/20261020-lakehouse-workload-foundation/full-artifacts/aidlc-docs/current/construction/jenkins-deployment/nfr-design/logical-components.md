# Logical Components: `jenkins-deployment`

| Component | Responsibility | NFR behavior |
|---|---|---|
| Git repository branches | Source of environment DAGs, configs, and Spark code | `dev`, `uat`, and `main` remain independent refs; promotion between UAT and production is governed by repository release policy. |
| Airflow DAG processor | Refresh Git bundles and parse DAG definitions | Uses configured refresh interval, reports fetch/import errors, and keeps versioned bundle metadata. |
| `lakehouse-dev` GitDagBundle | Supply development DAGs and artifacts | Tracks the feature ref selected by the deployment client; checks out `dags/`, `configs/`, and `notebooks/`; bundle name selects `dev`. |
| `lakehouse-uat` GitDagBundle | Supply UAT DAGs and artifacts | Tracks `uat`; checks out the same paths; bundle name selects `uat`. |
| `lakehouse-prod` GitDagBundle | Supply production DAGs and artifacts | Tracks `main`; checks out the same paths; bundle name selects `prod` config and `main` DAG ID prefix. |
| Airflow Git connection/secrets backend | Authenticate private repository fetches | Secrets are external and referenced by connection ID; read-only access and host verification are configured. |
| Airflow task execution environment | Resolve the recorded bundle version and execute DAG code | Must access the same versioned bundle checkout used for the DAG run; Spark application delivery/path semantics are verified at integration. |
| Branch-selection client | Change the dev bundle's tracking ref | Validates a non-reserved feature ref, changes only the dev bundle configuration, invokes the deployment apply/reload operation, and restores the prior ref if apply fails. It does not claim DAG parse readiness. |
| Jenkins CI pipeline | Validate and gate changes on `uat` and `main` | Does not upload artifacts or hold Airflow Git credentials; build status is not a bundle-refresh status. |

## Interaction Boundaries

- Airflow owns branch polling, parsing, bundle version pinning, and task execution.
- Git host owns repository availability and branch permissions.
- The deployment configuration manager owns applying the client's dev ref update and reloading/restarting the required Airflow components.
- Jenkins owns CI checks and branch gates only.
- Spark cluster remains externally managed and receives the application through the configured Spark submission mechanism.
