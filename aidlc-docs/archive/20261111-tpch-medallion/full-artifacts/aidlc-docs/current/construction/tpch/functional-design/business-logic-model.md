# Business Logic Model — tpch

## Bronze (`bronze_ingestion.py`)
```text
arguments = parse_task_args(TASK_ARGUMENTS)            # widgets in Jupyter, args in Airflow
entity, scale_factor = check_arguments(arguments)      # R1, R2
spark, config = start_spark_job("bronze_ingestion")    # Jupyter: from the resolver
started = now (UTC)
with duckdb in memory:
    CALL dbgen(sf = scale_factor)
    columns = DESCRIBE entity -> (name, duckdb type)
    schema  = spark types via the type map             # R5
    rows    = SELECT entity, DECIMAL columns as VARCHAR  # R6
    check the TPC-H count                              # R7
frame = spark DataFrame(rows), every column cast to schema
        + scale_factor decimal(4,3), bronze_ingestion_timestamp = started   # R8
table = qualified_table(config, tpch_<entity>_db_brz)
if table missing: create at table_location with frame   # R9
else: append frame
log JSON summary (rows_appended, created, ...)
```

## Silver (`silver_processing.py`)
```text
entity, lookback = check_arguments(parse_task_args(TASK_ARGUMENTS))   # R1, R3
spark, config = start_spark_job("silver_processing")
started = now (UTC)
source = qualified_table(config, tpch_<entity>_db_brz)
target = qualified_table(config, tpch_<entity>)
checkpoint = checkpoint_location(config, tpch_<entity>)               # R16
if lookback > 0:
    reset_checkpoint(spark, checkpoint)                               # R15
    stream_from = started - lookback days                             # R14
reader = readStream iceberg(source) [+ stream-from-timestamp]
foreachBatch(batch, batch_id):
    if batch_id already counted: skip counting                         # R17
    latest = newest row per MERGE_KEYS[entity]                         # R11
    if target missing: create empty from batch schema at table_location # R13
    MERGE INTO target USING latest                                     # R12
    counts[batch_id] = (rows read, rows after latest-per-key)
start with checkpointLocation = checkpoint, trigger availableNow; await
log JSON summary (batches, rows_read, rows_merged, checkpoint_reset, stream_from, ...)
```

## Workflow run order
For each entity: `tpch_<entity>_db_brz_load` → `tpch_<entity>_load`. The eight pairs are independent; the platform adds its own tasks around them.

## Failure behavior
| Situation | Result |
|---|---|
| Bad argument | Airflow: usage message, exit 2, the task fails before Spark work; Jupyter: `ValueError` |
| DuckDB extension download fails (no network) | bronze fails; nothing is written |
| TPC-H count rule broken | bronze fails before writing |
| Unmapped DuckDB type | bronze fails naming the column |
| Bronze schema differs from an existing table | the append fails; the table is unchanged |
| `checkpoint_path` missing or not `s3ckpt://` | silver fails naming the key, before streaming |
| Checkpoint key missing (platform) | silver fails at its first checkpoint access |
| MERGE fails in a batch | the stream fails; the checkpoint doesn't commit that batch, so the next run retries it (idempotent by R12) |
| Bronze snapshot that deletes or overwrites | the stream fails (bronze is append-only; a manual rewrite needs a silver reset) |
| Lookback reset, then failure before the first batch | the next run starts from bronze's first snapshot unless it passes the lookback again (documented) |
