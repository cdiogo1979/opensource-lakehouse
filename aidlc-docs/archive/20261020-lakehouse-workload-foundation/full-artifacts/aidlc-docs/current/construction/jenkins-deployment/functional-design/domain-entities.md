# Domain Entities: `jenkins-deployment`

This unit has no business-domain entities. Its deployment contract uses these technical records.

## `EnvironmentBundle`
- `name: str` — stable unique Airflow bundle name: `lakehouse-dev`, `lakehouse-uat`, or `lakehouse-prod`.
- `environment: str` — `dev`, `uat`, or `prod`.
- `tracking_ref: str` — selected feature branch for dev; fixed `uat` and `main` for UAT and production.
- `sparse_dirs: tuple[str, ...]` — the same `dags/`, `configs/`, and `notebooks/` directories for each branch-versioned bundle.
- `git_connection_id: str` — Airflow-managed connection reference; secret material is external to bundle kwargs.

## `DevBranchSelection`
- `requested_ref: str` — Git-valid, non-reserved feature branch selected by an authorized operator.
- `previous_ref: str` — current dev bundle tracking ref retained for rollback if apply fails.
- `apply_status: str` — applied, rejected, or failed; success means config apply/reload command succeeded, not that DAG parsing completed.

## `BundleRunVersion`
- `bundle_name: str` — bundle that supplied the DAG definition.
- `commit_id: str` — Git commit recorded by Airflow for the DAG run.
- `artifact_root: Path` — version-specific checkout used to locate config and Spark application files.
