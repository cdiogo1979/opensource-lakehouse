# Component Methods — TPC-H Medallion Subproject

Signatures and purpose only; rules and edge cases are detailed in Functional Design.

## C1 `bronze_ingestion.py`
| Name | Input → Output | Purpose |
|---|---|---|
| `TASK_ARGUMENTS`, `WIDGET_LIST` | constants | `entity` (required), `scale_factor` (`0.01`) |
| `ENTITIES`, `parse_scale_factor(text)` | `str` → `Decimal` | As in `generate_tpch.py` |
| `check_arguments(arguments)` | `dict` → `(entity, scale_factor)` | Validation in the notebook (the parser doesn't check) |
| `bronze_table_name(entity)` | `str` → `str` | `tpch_<entity>_db_brz` |
| `qualified_table(config, table)` | `EnvironmentConfig`, `str` → `str` | `<catalog_name>.<database_name>.<table>` |
| `table_location(config, table)` | → `str` | `<storage_path>/<catalog_name>/<database_name>/<table>` (one `/` between parts) |
| `generate_entity(entity, scale_factor)` | → `pyarrow.Table` | DuckDB `CALL dbgen`, the entity's rows |
| `append_bronze(spark, config, entity, scale_factor, rows)` | → `int` | Add the two columns, create the table at its location if missing, append; returns rows appended |
| `summary(...)` | → `dict` | The JSON log record |

## C2 `silver_processing.py`
| Name | Input → Output | Purpose |
|---|---|---|
| `TASK_ARGUMENTS`, `WIDGET_LIST` | constants | `entity` (required), `silver_lookback_days` (`0`) |
| `MERGE_KEYS` | `dict[str, tuple[str, ...]]` | The eight entities and their keys (FR-4) |
| `check_arguments(arguments)` | `dict` → `(entity, lookback_days)` | Entity in `MERGE_KEYS`; non-negative integer |
| `silver_table_name(entity)` | `str` → `str` | `tpch_<entity>` |
| `qualified_table(config, table)`, `table_location(config, table)` | as in bronze | Defined in this notebook too (D3) |
| `checkpoint_location(config, table)` | → `str` | `<checkpoint_path>/tpch/<table>`; refuses a missing `checkpoint_path` |
| `latest_per_key(batch, keys)` | DataFrame → DataFrame | The newest row per key by `bronze_ingestion_timestamp` |
| `merge_condition(keys)` | `tuple` → `str` | `t.k = s.k AND ...` |
| `merge_batch(batch, batch_id)` | foreachBatch callback | Latest per key; create silver if missing; `MERGE INTO`; counts rows per batch ID |
| `reset_checkpoint(spark, location)` | → `bool` | Delete this entity's checkpoint (lookback only) |
| `start_timestamp_ms(lookback_days, now)` | → `int` | `now - lookback_days` in ms for `stream-from-timestamp` |
| `run_stream(spark, config, entity, lookback_days)` | → `dict` | The availableNow stream; returns the counts for the summary |
| `summary(...)` | → `dict` | The JSON log record |
