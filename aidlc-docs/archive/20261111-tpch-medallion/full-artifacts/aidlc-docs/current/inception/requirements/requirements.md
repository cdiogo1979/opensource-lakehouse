# Requirements — TPC-H Medallion Subproject

## Intent Analysis
- **Request**: a `tpch` subproject with bronze and silver: bronze generates TPC-H data with the existing DuckDB generator and saves it to bronze tables; silver merges bronze changes into silver tables using bronze CDC; check the naming conventions for tables and workflows; follow the standard notebook structure; update AGENTS.md, including the Jupyter helpers notebooks use. Model: `test_aidlc/notebooks/P2`, simplified.
- **Type**: new subproject plus convention updates. **Depth**: standard.
- **Answers**: `requirement-verification-questions.md` (Q1 to Q8).

## Functional Requirements

### FR-1 Subproject layout
- `workflows/tpch/tpch_medallion.json`; `notebooks/workload/tpch/bronze/bronze_ingestion.py`; `notebooks/workload/tpch/silver/silver_processing.py`.

### FR-2 Naming conventions (from P2; documented in AGENTS.md and the README)
- **Notebooks**: `<layer>_<action>.py` in the layer folder (`bronze_ingestion.py`, `silver_processing.py`).
- **Bronze tables**: `<project>_<entity>_<source>_brz` (`tpch_region_db_brz`, source `db` for the DuckDB generator).
- **Silver tables**: `<project>_<entity>` (`tpch_region`).
- **Table locations**: `<storage_path>/<catalog_name>/<database_name>/<table>` from the environment config (inside the product namespace's Polaris location). All tables live in the environment's single namespace (`database_name`); products can't create namespaces, so the layer is part of the name.
- **Workflows**: `<project>_<purpose>` (`tpch_medallion`), unique in the repository; **tasks**: `<target_table>_load` (`tpch_region_db_brz_load` for bronze, `tpch_region_load` for silver).
- **Checkpoints**: `<checkpoint_path>/<project>/<target_table>` (`.../tpch/tpch_region` for silver's `tpch_region`).

### FR-3 Bronze ingestion (`bronze_ingestion.py`)
- **Arguments and widgets**: `entity` (required: one of the eight TPC-H entities) and `scale_factor` (default `0.01`; 0.001 to 1, at most three decimals); no environment widget (the environment resolver selects it).
- **Generation**: its own copy of the DuckDB TPC-H generation (Q4 C): `CALL dbgen(sf=…)` in memory, the entity's rows.
- **Write**: append to `tpch_<entity>_db_brz`, created if missing (Iceberg, the FR-2 location), with the entity's columns plus `scale_factor` and `bronze_ingestion_timestamp`. Append-only (Q2 A), so bronze changes are inserts only.
- **Log**: one JSON summary (layer, entity, scale factor, rows appended, destination table).

### FR-4 Silver processing (`silver_processing.py`)
- **Arguments and widgets**: `entity` (required) and `silver_lookback_days` (default `0`, a non-negative integer); lookback on silver only.
- **Merge keys**: a constant mapping each entity to its key: `region`: `r_regionkey`; `nation`: `n_nationkey`; `supplier`: `s_suppkey`; `customer`: `c_custkey`; `part`: `p_partkey`; `partsupp`: `ps_partkey`, `ps_suppkey`; `orders`: `o_orderkey`; `lineitem`: `l_orderkey`, `l_linenumber`.
- **CDC**: Spark Structured Streaming on the bronze Iceberg table (appended snapshots), `trigger(availableNow=True)`, checkpoint at the FR-2 checkpoint location from `checkpoint_path` in `configs/<env>.yml`. `silver_lookback_days = 0` resumes from the checkpoint; `N > 0` resets this entity's checkpoint and replays the bronze snapshots committed in the last N days.
- **Merge**: per micro-batch, the latest row per merge key (by `bronze_ingestion_timestamp`), `MERGE INTO tpch_<entity>` (created if missing, FR-2 location): insert new keys; update existing keys only when the bronze row is newer. Idempotent.
- **Log**: one JSON summary (layer, entity, lookback, cutoff, rows merged, source and destination tables).

### FR-5 Configuration
- `configs/{dev,uat,prod}.yml` gain `checkpoint_path: s3ckpt://<bucket>/checkpoints` (the product's bucket for that environment: `bucket-default-dev`, `bucket-default-uat`, `bucket-default`; CR-2).

### FR-6 Workflow
- `tpch_medallion`: manual schedule; 16 tasks `tpch_<entity>_db_brz_load` (bronze, `args` `--entity <entity>`) and `tpch_<entity>_load` (silver, `runs_after` its bronze task); DAG `default-<env>-tpch_medallion`.

### FR-7 Notebook standard and AGENTS.md
- Both notebooks follow the standard (title; Initialization; Imports; own sections; Execution) and use `start_spark_job`, `parse_task_args` with a widget declaration, and the Jupyter helpers.
- **AGENTS.md** documents the naming conventions (FR-2) and which Jupyter helpers a notebook includes: Initialization (`lakehouse-install-requirements`, `jupyter_environment_resolver.py`), and, for notebooks with task arguments, a widgets section (`TASK_ARGUMENTS`, `WIDGET_LIST`, `jupyter_input_widget_helper.py`). The structure test follows.

### FR-8 Tests and docs
- Unit tests (fakes for Spark and DuckDB where needed) and Hypothesis properties for the pure rules; README updates; knowledge per Q8.

## Change request CR-1 (2026-11-11, during Requirements Analysis)
- **Request**: "Task <target_table>_load tpch_region_load Checkpoint <checkpoint_path>/<project>/<target_table>".
- **Decision**: task names are `<target_table>_load` and checkpoints `<checkpoint_path>/<project>/<target_table>` (FR-2, FR-6); this replaces `<layer>_<entity>` and `<checkpoint_path>/<project>/<notebook>/<entity>`.

## Change request CR-2 (2026-11-11, Application Design, after the platform intent)
- **Platform answer**: the closed `opensource-lakehouse-infra` intent `20261111-spark-s3-checkpoints` added streaming checkpoints: `checkpoint_path` uses the scheme `s3ckpt://<bucket>/checkpoints` (Iceberg's streaming offsets need a non-`s3` scheme), with a per-bucket checkpoint key mounted by the platform (Airflow: the run's environment; Jupyter: `dev` for owners and developers). Products do nothing else.
- **Decision**: FR-5 uses that form; the open risk below is resolved (probe in `audit.md`).

## Change request CR-3 (2026-11-11, Build and Test)
- **Finding**: in the first UAT run all eight bronze jobs, then six silver jobs, ran at once in the run's single Spark container; two silver jobs were OOM-killed (exit 137) and the lineitem bronze table creation hit a Polaris to RustFS read timeout.
- **Decision** (user: "Two lanes"): FR-6's workflow runs bronze tasks in sequence and each silver task after its bronze task and the previous silver task (at most two Spark jobs), with one retry per task after 60 s. A platform follow-up: a per-workflow parallelism limit.

## Non-Functional Requirements
- **NFR-1 Idempotence**: rerunning bronze appends a new batch; rerunning silver with a lookback never changes a row to an older one.
- **NFR-2 No secrets** in notebooks, configs or workflows.
- **NFR-3 Compatibility**: `sample` and its workflows are unchanged.

## Open risk (Application Design probe) — resolved by CR-2
- **Checkpoint storage**: Spark's checkpoint writes use the Hadoop `s3a://` filesystem; the platform gives Spark storage credentials only through Polaris for Iceberg table files. The probe checks whether a checkpoint can be written at the configured `checkpoint_path` in an Airflow run and in Jupyter; if not, the user decides the next step.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q7: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q7: A) |
| Resiliency Baseline | No | Requirements Analysis (Q7: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |
