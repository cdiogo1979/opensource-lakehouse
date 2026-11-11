# Requirement Verification Questions — TPC-H Medallion Subproject

Asked and answered interactively on 2026-11-11. The user also gave the model to follow: `test_aidlc/notebooks/P2` (`bronze/bronze_ingestion.py`, `silver/silver_processing.py`) for naming of notebooks, tables and table locations, widgets ("lookback on silver only, environment is not needed") and logging, simplified; "in silver a constant with mapping between entity and merge key should be created"; "example naming convention tcph_region_db_brz (bronze), tcph_region (silver)".

## Q1 Prefix
A) `tpch` (Recommended) — B) `tcph`, as written

[Answer]: A

## Q2 Bronze writes
A) Append-only, like P2: each run appends the generated rows with `bronze_ingestion_timestamp`; silver keeps the latest row per merge key (Recommended) — B) Upsert into bronze

[Answer]: A

## Q3 Bronze scope
A) One run for all entities, two workflow tasks (Recommended) — B) One task per entity (both notebooks take the entity)

[Answer]: B

## Q4 Generator reuse
A) Shared module in `notebooks/common/` (Recommended) — B) Import from `sample` — C) Copy into the bronze notebook

[Answer]: C

## Q5 Silver CDC position
A) Last processed bronze snapshot stored in the silver table (Recommended) — B) Always a lookback window — X) Other

[Answer]: X. First "can spark streaming not use its checkpoints?"; after the explanation that the run container is discarded and Spark has no S3 credentials outside Polaris' per-table ones, and the options snapshot position / streaming with a local checkpoint / a platform checkpoint store: "i add checkpoint location config in yaml". Decision: Spark Structured Streaming on the bronze table with a checkpoint location from the environment YAML, as in P2; whether Spark can write the checkpoint there is probed in Application Design, and the user decides if it can't.

## Q6 Workflow
A) One workflow `tpch_medallion` with `bronze_<entity>` and `silver_<entity>` tasks (Recommended) — B) Two workflows

[Answer]: A

## Q7 Extensions
A) Property-based testing, partial; Security and Resiliency off (Recommended) — B) All off

[Answer]: A

## Q8 Knowledge
A) Add `aidlc-docs/knowledge/tpch/`; replace the stale `opensource-lakehouse` documents with a current repository-level design (Recommended) — B) Add `tpch` only

[Answer]: A
