# Business Rules — tpch

## Arguments (checked in the notebooks; the parser only reads strings)
- **R1 Entity**: one of the eight entities, exactly as written; anything else is a `ValueError` naming the accepted values.
- **R2 Scale factor** (bronze): as `generate_tpch.py`: a decimal from 0.001 to 1 with at most three decimal places.
- **R3 Lookback** (silver): digits only (`0` to `3650`); no sign, spaces or decimals.
- **R4 Errors**: in Airflow an argument error prints `<notebook>.py: <message>` and exits 2; in Jupyter it raises.

## Bronze
- **R5 Schema**: the Spark schema comes from DuckDB's `DESCRIBE <entity>` through the type map (INTEGER `int`, BIGINT `bigint`, DECIMAL(p,s) `decimal(p,s)`, DATE `date`, VARCHAR `string`); an unmapped type is an error naming the column. Spark's inferred types are never used (pandas would turn DECIMAL into `double` and DATE into `timestamp`).
- **R6 Exact values**: the DuckDB query casts DECIMAL columns to VARCHAR, and Spark casts every column to its mapped type, so decimals are exact.
- **R7 Generation**: in memory (`duckdb.connect()`), `CALL dbgen(sf=<scale factor>)`, `SELECT` of the entity; the entity name is checked (R1) before it reaches SQL. Generated row counts are **not** checked and no count query runs (user, Code Generation: counts are expensive); `rows_appended` is the generated frame's length.
- **R8 Added columns**: `scale_factor` as `decimal(4,3)`; `bronze_ingestion_timestamp`, one UTC timestamp taken once per run.
- **R9 Write**: when the table is missing, create it with this run's rows at its location (`writeTo(...).using("iceberg").tableProperty("location", <location>).create()`); otherwise append. Each run adds one snapshot. A schema mismatch with an existing table fails the run.

## Silver
- **R10 Stream**: an Iceberg streaming read of the bronze table, `trigger(availableNow=True)`, `checkpointLocation` = the silver checkpoint (R16). Without a checkpoint it starts at bronze's first snapshot, or at `stream-from-timestamp` for a lookback (R14).
- **R11 Latest per key**: in each micro-batch, one row per merge key: the one with the greatest `bronze_ingestion_timestamp` (rows of one bronze run share a timestamp and keys are unique within a run, so there are no ties).
- **R12 Merge**: `MERGE INTO <silver> t USING <batch view> s ON <t.k = s.k for every key>`; `WHEN MATCHED AND s.bronze_ingestion_timestamp > t.bronze_ingestion_timestamp THEN UPDATE SET *`; `WHEN NOT MATCHED THEN INSERT *`. A row is never replaced by an older or equal one, so any replay is idempotent.
- **R13 Silver creation**: when missing, created empty from the batch schema at its location before the first MERGE (through the batch's session).
- **R14 Lookback**: `silver_lookback_days = 0` resumes from the checkpoint. `N > 0` deletes this entity's checkpoint folder first (R15), then starts with `stream-from-timestamp` = the run's start minus N × 86 400 000 ms. Afterwards, the new checkpoint continues normally.
- **R15 Reset safety**: only a path equal to the entity's checkpoint location (R16) is deleted, recursively; an absent checkpoint is not an error.
- **R16 Checkpoint location**: `<checkpoint_path>/tpch/tpch_<entity>`; a missing or empty `checkpoint_path`, or one that doesn't start with `s3ckpt://`, is an error naming the key.
- **R17 Counting**: counts are taken inside `foreachBatch`, once per batch ID (a retried batch ID is counted once). The outer session never reads silver for the summary (it can hold a cached version).

## Names
- **R18**: bronze `tpch_<entity>_db_brz`, silver `tpch_<entity>`; qualified name and location from the config (domain-entities.md). `storage_path` and `checkpoint_path` may end with `/`; exactly one `/` joins each part.

## Workflow
- **R19**: `tpch_medallion`, `schedule: null`, tags `tpch`, `bronze`, `silver`; 16 tasks: `tpch_<entity>_db_brz_load` (`bronze/bronze_ingestion.py`, `--entity <entity>`) and `tpch_<entity>_load` (`silver/silver_processing.py`, `--entity <entity>`, `runs_after` its bronze task). No lookback argument (D8).

## Configs
- **R20**: `checkpoint_path: "s3ckpt://bucket-default-dev/checkpoints"` (dev), `"s3ckpt://bucket-default-uat/checkpoints"` (uat), `"s3ckpt://bucket-default/checkpoints"` (prod).

## Property-based tests (PBT partial: PBT-02, 03, 07, 08, 09)
- **P1** (R18): for generated configs and entities, the location is the four parts joined by exactly one `/` with no `//` after the scheme, and the qualified name splits back into catalog, database and table (round trip).
- **P2** (R16): the checkpoint location starts with `checkpoint_path`, ends with `/tpch/tpch_<entity>`, and is refused for any non-`s3ckpt://` path.
- **P3** (R5): for generated DuckDB type lists, the type map gives the documented Spark type for every supported type and refuses every other.
- **P4** (R3): exactly the strings `0` to `3650` in digits are accepted, and the value round-trips to its text.
- **P5** (R12): the merge condition names every key once, in `MERGE_KEYS` order, joined by `AND`.
- **P6** (R11, R12, a pure reference model): applying any sequence of bronze batches to an empty silver with the R11 and R12 rules, in any batch grouping, gives the newest row per key; replaying any subset again changes nothing. The Spark expression is checked against it live in Build and Test.

Hypothesis settings as in the repository: derandomized, shrinking on, reproduction blob printed.
