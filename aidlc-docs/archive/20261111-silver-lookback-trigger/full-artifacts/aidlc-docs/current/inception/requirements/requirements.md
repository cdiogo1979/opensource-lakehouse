# Requirements — Silver Lookback as a Trigger Value

Depth: minimal (documentation only). Stages approved in advance by the user.

## Request
"proceed and merge the update to uat and main branches as its just documentation" (the follow-up recorded at the close of platform intent 20261111-airflow-task-params).

## Requirements
- **FR-1** README (tpch, Reprocess silver) and the silver notebook's title cell: in uat or prod, a lookback is a trigger value, for example `{"tpch_<entity>_load": {"silver_lookback_days": "<N>"}}` in the DAG's `task_args`, for the entities to reprocess; no workflow edit.
- **FR-2** Canonical tpch application design D8 updated at closure.
- **FR-3** Merge to `uat` and `main` (fast-forward; both are behind or equal to `origin/main`).
- **NFR-1** pytest and `scripts/code_quality.sh all` still pass.
