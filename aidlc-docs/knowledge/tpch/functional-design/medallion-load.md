# Functional Design — tpch Medallion Load

The bronze and silver load rules of the `tpch` subproject. Architecture: [`../application-design.md`](../application-design.md).

## Entities
| Entity | Merge key |
|---|---|
| region | `r_regionkey` |
| nation | `n_nationkey` |
| supplier | `s_suppkey` |
| customer | `c_custkey` |
| part | `p_partkey` |
| partsupp | `ps_partkey`, `ps_suppkey` |
| orders | `o_orderkey` |
| lineitem | `l_orderkey`, `l_linenumber` |

## Names and locations
| Item | Form | Dev example |
|---|---|---|
| Bronze table | `tpch_<entity>_db_brz` | `lakehouse_dev.default_lhdev.tpch_region_db_brz` |
| Silver table | `tpch_<entity>` | `lakehouse_dev.default_lhdev.tpch_region` |
| Location | `<storage_path>/<catalog_name>/<database_name>/<table>` (one `/` between parts) | `s3a://bucket-default-dev/lakehouse_dev/default_lhdev/tpch_region` |
| Checkpoint | `<checkpoint_path>/tpch/tpch_<entity>`; `checkpoint_path` must be `s3ckpt://` | `s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region` |

## Arguments (checked in the notebooks; the parser only reads strings)
- `entity`: one of the eight, exactly as written.
- `scale_factor` (bronze, default `0.01`): a decimal from 0.001 to 1 with at most three decimal places.
- `silver_lookback_days` (silver, default `0`): `0` to `3650` in digits (no sign, spaces, decimals or leading zeros).
- A bad value prints `<notebook>.py: <message>` and exits 2 in Airflow; raises in Jupyter.

## Bronze
- **Generation**: `duckdb.connect()` in memory, `CALL dbgen(sf=<scale factor>)`, `SELECT` of the entity (the name is checked first). No row counts are checked or queried (expensive).
- **Schema**: from DuckDB's `DESCRIBE`: INTEGER `int`, BIGINT `bigint`, DECIMAL(p,s) `decimal(p,s)`, DATE `date`, VARCHAR `string`; any other type is an error. DuckDB returns DECIMAL and DATE columns as text and Spark casts every column to its type, so values are exact (pandas inference would give `double` and `timestamp`).
- **Added columns**: `scale_factor` `decimal(4,3)`; `bronze_ingestion_timestamp` `timestamp`, one UTC value per run.
- **Write**: create the table with the run's rows at its location when missing, else append; a schema mismatch fails the run.

## Silver
- **Stream**: Iceberg streaming read of bronze, `trigger(availableNow=True)`, the checkpoint above; without a checkpoint it starts at bronze's first snapshot (or at `stream-from-timestamp` for a lookback).
- **Per micro-batch**: the newest row per merge key by `bronze_ingestion_timestamp`; silver created empty from the batch schema at its location when missing; then `MERGE INTO <silver> t USING <view> s ON <keys> WHEN MATCHED AND s.bronze_ingestion_timestamp > t.bronze_ingestion_timestamp THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *`. A row is never replaced by an older or equal one.
- **Lookback**: N > 0 deletes exactly the entity's checkpoint folder (the path is derived from the config, nothing else can be deleted), then streams from the run's start minus N days.
- **Counts**: rows read and rows merged per batch ID, inside `foreachBatch`.

## Logs (JSON)
- **Start record** before any work, and **summary** at the end, both with `environment`, `bucket`, `catalog`, `database`, `table`, `location`; silver also `source`, `source_location`, `checkpoint`, `checkpoint_bucket`.
- **Bronze summary**: `layer`, `entity`, `scale_factor`, `bronze_ingestion_timestamp`, `rows_appended` (the generated frame's length), `created`.
- **Silver summary**: `layer`, `entity`, `lookback_days`, `stream_from`, `checkpoint_reset`, `batches`, `rows_read`, `rows_merged`.

## Workflow
`tpch_medallion`: `schedule: null`, tags `tpch`, `bronze`, `silver`. Bronze tasks run in the order region, nation, supplier, customer, part, partsupp, orders, lineitem; each silver task `runs_after` its bronze task and the previous silver task. Every task has `retries: 1`, `retry_delay_seconds: 60`; a retried bronze task may append its batch twice, which silver absorbs.

## Failure behavior
| Situation | Result |
|---|---|
| Bad argument | exit 2 before Spark work (Airflow); `ValueError` (Jupyter) |
| DuckDB extension download fails | bronze fails; nothing written |
| Unmapped DuckDB type, or a schema mismatch | bronze fails naming the column; the table is unchanged |
| `checkpoint_path` missing or not `s3ckpt://` | silver fails before streaming |
| MERGE fails in a batch | the batch isn't committed; the next run retries it (idempotent) |
| A bronze snapshot deletes or overwrites rows | the stream fails (bronze is append-only) |
| Too many Spark jobs in one container or Jupyter server | OOM kills (exit 137; kernel restart); the two lanes and one notebook at a time avoid it |

## Properties (Hypothesis, partial PBT)
P1 locations and qualified names; P2 checkpoint location and scheme; P3 the type map; P4 lookback parsing round trip; P5 the merge condition; P6 a reference merge model: any batch grouping gives the newest row per key, and replays change nothing.
