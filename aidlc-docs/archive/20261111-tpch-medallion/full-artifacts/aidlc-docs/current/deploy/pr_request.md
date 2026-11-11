# PR request — Add the tpch subproject (TPC-H bronze ingestion and silver streaming merge)

The pull request from `tpch-medallion` into `main` was opened by the user with this description; Jenkins `default_cd` passed on it. Nothing is merged.

## Problem
The repository had no medallion example on the platform: no bronze ingestion into Iceberg, no change-data merge into silver, and no conventions for table names, locations, workflows, tasks and checkpoints.

## Solution
- **Bronze** `notebooks/workload/tpch/bronze/bronze_ingestion.py`: one TPC-H entity generated in memory with DuckDB, appended to `tpch_<entity>_db_brz` with `scale_factor` and `bronze_ingestion_timestamp`; exact DuckDB types; table created at `<storage_path>/<catalog_name>/<database_name>/<table>` on the first run; no count queries.
- **Silver** `notebooks/workload/tpch/silver/silver_processing.py`: Structured Streaming `availableNow` on bronze, checkpoint `<checkpoint_path>/tpch/tpch_<entity>` (`s3ckpt://`), `MERGE INTO tpch_<entity>` of the newest row per key (`MERGE_KEYS`), updates only with newer rows; `silver_lookback_days` resets the checkpoint and replays the last N days.
- **Workflow** `tpch_medallion`: 16 tasks in two lanes (at most two Spark jobs in the run's container), one retry per task.
- **Logs**: a JSON start record and summary per run with environment, bucket, catalog, database, tables, locations and checkpoint.
- **Configs** `checkpoint_path` per environment; **docs**: AGENTS.md conventions and Jupyter helpers, README subproject section.

## Verification
See `construction/build-and-test/build-and-test-summary.md`: code quality clean; tests local 112 passed (2 DuckDB skips), 21 in the runtime image; Jenkins `default_cd` SUCCESS; UAT 21/21; Jupyter bronze and silver with a lookback in dev. Not run: an Airflow lookback, a production run.

## Deployment
Ordered steps: [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
- Tables can't be dropped by the product writer; a schema mistake needs an owner or the platform team.
- A lookback in uat or prod needs a temporary workflow edit (platform params follow-up).
- Each checkpoint must have one writer at a time; a dev notebook and a dev stream share the checkpoint.
- Jupyter servers have 2 GiB: one Spark notebook at a time (platform follow-up to raise it).
