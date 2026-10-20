# Technology Decisions: `jenkins-deployment`

| Area | Decision | Rationale / constraint |
|---|---|---|
| Airflow artifact delivery | Airflow 3 GitDagBundles using `airflow.providers.git.bundles.git.GitDagBundle` | Airflow fetches branch content and provides commit-versioned DAG runs. |
| Environment separation | `lakehouse-dev` has an operator-selected feature ref; `lakehouse-uat` tracks `uat`; `lakehouse-prod` tracks `main` | Lets a developer test a branch without moving shared UAT or production refs. |
| Branch selection client | Repository-owned Python CLI that atomically updates only the dev bundle config and invokes a deployment-specific apply/reload command | Airflow UI does not natively edit `tracking_ref`; target-specific config manager/restart behavior is external. |
| Bundle content | Sparse checkout of `dags/`, `configs/`, and `notebooks/`; repository root is bundle root | Each branch version supplies its DAG environment ID and matching artifacts. |
| Git authentication | Airflow Git connection or secrets backend referenced through `git_conn_id` | Keeps credentials outside bundle kwargs/source; use read-only access and trusted host verification. |
| Jenkins | CI validation and branch gates only | It does not publish artifacts or select the dev test ref. |
| Property-based testing | Hypothesis with pytest | Tests valid/invalid ref handling, bundle isolation, and rollback invariants. |
| Runtime versions | Airflow 3 required; provider/runtime versions not pinned until platform selection | Git provider and deployment reload compatibility depend on the managed Airflow release. |

## PBT-09 Compliance

- **Status**: Applicable.
- **Properties**: Exact UAT/prod refs, mutable dev ref only, protected-ref rejection, atomic update, rollback on apply failure, bundle uniqueness, and run-version path selection.
- **External verification**: Confirm installed Git provider, Git connection, and the target-specific configuration apply/reload command against the managed Airflow deployment.
