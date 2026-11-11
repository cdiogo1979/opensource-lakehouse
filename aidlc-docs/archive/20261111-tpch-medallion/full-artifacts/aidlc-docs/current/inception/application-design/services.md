# Services — TPC-H Medallion Subproject

No new service. The platform's DAG factory runs the workflow; each task is one `spark-submit` of a notebook in the run's Spark container.

## Airflow run (`default-<env>-tpch_medallion`, `prod` or `uat`)
1. The platform's `create_cluster`, `install_requirements` (DuckDB from `requirements.txt`) and `validate_environment` run first; the run container holds this environment's checkpoint key.
2. For each entity, `tpch_<entity>_db_brz_load` runs C1 with `--entity <entity>`, then `tpch_<entity>_load` runs C2 with `--entity <entity>` (`runs_after` its bronze task). Entities are independent; the factory orders tasks only by `runs_after`.
3. A rerun appends a new bronze batch per entity; silver picks up only the new snapshot from its checkpoint.
4. A lookback (D8): temporarily add `--silver-lookback-days N` to the silver tasks' `args` in `tpch_medallion.json`, push to the environment's branch, run, then revert. The workflow normally passes none.

## Jupyter session (`dev`, owner or developer)
1. Initialization installs `requirements.txt` and runs the environment resolver (`spark`, `config` from `dev.yml`); the server holds the dev checkpoint key.
2. The widget cell creates `entity` (and `scale_factor` or `silver_lookback_days`); the user runs the rest.
3. Interactive runs use the same `dev` checkpoint path as any other dev run (accepted: dev is a sandbox).
