# Application Design — tpch

The `tpch` subproject loads TPC-H data through a bronze and a silver layer, as the repository's medallion example. History: the [TPC-H Medallion intent archive](../../archive/20261111-tpch-medallion/intent-summary.md). Repository-wide rules: [`../opensource-lakehouse/application-design.md`](../opensource-lakehouse/application-design.md).

## Components
| Component | Path | Role |
|---|---|---|
| Bronze ingestion | `notebooks/workload/tpch/bronze/bronze_ingestion.py` | Generates one TPC-H entity in memory with DuckDB and appends it to `tpch_<entity>_db_brz` |
| Silver processing | `notebooks/workload/tpch/silver/silver_processing.py` | Streams the bronze table's new snapshots and merges the newest row per key into `tpch_<entity>` |
| Workflow | `workflows/tpch/tpch_medallion.json` | 16 tasks, `tpch_<entity>_db_brz_load` and `tpch_<entity>_load`, in two lanes |
| Configs | `configs/{dev,uat,prod}.yml` | `storage_path`, `catalog_name`, `database_name`, `checkpoint_path` |
| Tests | `tests/tpch/` | Pure rules with Hypothesis (P1 to P6); DuckDB generation; the workflow shape |

Shared helpers (`notebooks/common/`) are used unchanged: `start_spark_job`, `parse_task_args` (with each notebook's `TASK_ARGS_DEFINITION` and Jupyter `TASK_ARGS_VALUES`), and the Jupyter resolver.

## Decisions
| # | Decision | Reason |
|---|---|---|
| D1 | Bronze is append-only, one batch (one Iceberg snapshot) per run, with `scale_factor` and `bronze_ingestion_timestamp` | Bronze changes are inserts, so silver's change feed is the stream of appended snapshots |
| D2 | Silver uses Spark Structured Streaming on the bronze Iceberg table (`trigger(availableNow=True)`, `foreachBatch` `MERGE INTO`) with an `s3ckpt://` checkpoint | Durable incremental processing; the platform's streaming checkpoints (`checkpoint_path`) |
| D3 | Each notebook defines its own names and locations from the config; no shared naming module | User decision; the conventions are documented in AGENTS.md |
| D4 | Tables are created by the first run at an explicit location `<storage_path>/<catalog_name>/<database_name>/<table>` | The product writer can create but not drop tables |
| D5 | `silver_lookback_days = N > 0` deletes the entity's checkpoint and restarts with `stream-from-timestamp` N days back; MERGE only takes newer rows, so a replay is idempotent | Repair without duplicates |
| D6 | Silver counts rows inside `foreachBatch`, once per batch ID, and never reads silver from the outer session for its summary | The outer session caches a table it created; `recentProgress` repeats batches |
| D7 | Two lanes: bronze tasks in sequence; each silver task after its bronze task and the previous silver task; one retry per task after 60 s | A run's tasks share one Spark container; eight concurrent jobs were OOM-killed in UAT |
| D8 | The workflow passes no lookback; in uat or prod a lookback is a temporary workflow edit, in dev the notebook's `TASK_ARGS_VALUES` | The platform doesn't template task arguments (workflow params are a platform follow-up) |

## Platform contract used
- `start_spark_job` (Airflow) or the resolver (Jupyter) for the session and config; Polaris tables at explicit locations; `s3ckpt://` checkpoints with the platform-mounted key (Airflow: the run's environment; Jupyter: dev for owners and developers).
- One Spark container per DAG run; tasks are separate `spark-submit` JVMs in it.
- Jupyter servers have a 2 GiB limit: one Spark notebook at a time.

## Data flow
Workflow → bronze (DuckDB `dbgen` in memory → append to `tpch_<entity>_db_brz`) → silver (availableNow stream of new bronze snapshots, checkpoint `<checkpoint_path>/tpch/tpch_<entity>` → newest row per key → `MERGE INTO tpch_<entity>`).

## Verification and limits
- **Verified 2026-11-11**: code quality clean; tests 112 local (2 DuckDB skips), 21 in the Spark runtime image; Jenkins `default_cd` on the pull request; UAT `default-uat-tpch_medallion` 21/21 on `7a07ce9`; Jupyter bronze and silver (incremental, rerun, lookback) in dev.
- **Not run**: an Airflow lookback; a production run.
- **Limits**: the writer can't drop tables; a lookback in uat or prod needs a workflow edit; one writer per checkpoint (a dev notebook and a dev stream share it); a replay rewrites matched silver files once (a new snapshot with unchanged values); bronze snapshots that delete or overwrite rows stop the stream.
