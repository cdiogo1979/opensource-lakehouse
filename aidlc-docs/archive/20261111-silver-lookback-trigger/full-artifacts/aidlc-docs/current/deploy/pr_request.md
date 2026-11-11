# Change — Silver lookback as a trigger value

Documentation only. README (tpch, Reprocess silver) and the silver notebook's title cell now say that a lookback in uat or prod is a trigger value in the DAG's `task_args` (for example `{"tpch_region_load": {"silver_lookback_days": "7"}}`), using the platform feature from intent 20261111-airflow-task-params, instead of a temporary workflow edit. Canonical tpch design D8 updated. Merged to `uat` and `main` by fast-forward at the user's request.
