# Code Generation Plan — tpch

The single source of truth for Code Generation of this unit. Workspace root: `/Users/carlosdiogo/code_repo/opensource-lakehouse-sample-dp` (brownfield; existing files are changed in place). Nothing is committed or pushed in this stage.

## Unit context
- **Unit**: `tpch` (the only unit); no user stories. Traceability: FR-1 to FR-8, CR-1, CR-2; Application Design D1 to D8; Functional Design R1 to R20, P1 to P6.
- **Dependencies**: the shared helpers in `notebooks/common/` (unchanged); the platform contract (`start_spark_job`, `parse_task_args`, Polaris tables at explicit locations, `s3ckpt://` checkpoints); DuckDB from `requirements.txt`.
- **Owned entities**: the bronze and silver tables of the eight entities, the silver checkpoints.

## Steps
- [x] **Step 1 — Configs (FR-5, R20)**: add `checkpoint_path` to `configs/dev.yml`, `uat.yml`, `prod.yml`, with a comment. Test: extend the config-loader tests, so every environment has an `s3ckpt://` path in its own bucket.
- [x] **Step 2 — Bronze notebook (FR-3, R1, R2, R4 to R9, R18)**: `notebooks/workload/tpch/bronze/bronze_ingestion.py`, in the notebook standard:
  - title cell, Initialization, Imports;
  - Task arguments (`TASK_ARGUMENTS`, `WIDGET_LIST`, the widget helper);
  - TPC-H rules: `ENTITIES`, `parse_scale_factor`, count checks, copied from `generate_tpch.py` (Q4 C);
  - Names: `bronze_table_name`, `qualified_table`, `table_location`;
  - Schema: `spark_type`, `entity_schema`, the select with decimals as VARCHAR;
  - Generate and write: `generate_entity`, `append_bronze`;
  - Summary; Execution.
- [x] **Step 3 — Silver notebook (FR-4, R1, R3, R4, R10 to R18)**: `notebooks/workload/tpch/silver/silver_processing.py`, in the notebook standard:
  - Task arguments; `MERGE_KEYS`;
  - Names: `silver_table_name`, `bronze_table_name`, `qualified_table`, `table_location`, `checkpoint_location`;
  - Merge rules: `merge_condition`, `merge_sql`, `latest_per_key`, and the pure reference `apply_batches` used by P6;
  - Stream: `start_timestamp_ms`, `reset_checkpoint`, `merge_batch` with per-batch-ID counts, `run_stream`;
  - Summary; Execution.
- [x] **Step 4 — Workflow (FR-6, R19)**: `workflows/tpch/tpch_medallion.json` with 16 tasks. Checked by the platform validator (`lakehouse-validate-workflows`, if available locally) and a repository test.
- [x] **Step 5 — Tests (FR-8, P1 to P6)**:
  - new `tests/tpch/` with `conftest.py` (path and fakes as in `workload_foundation`), `test_bronze_ingestion.py` and `test_silver_processing.py`;
  - examples: arguments, names, type map, schema and select, DuckDB generation of every entity at a small scale factor, merge SQL, lookback timestamp, checkpoint reset path checks with a fake filesystem, summaries;
  - properties P1 to P6;
  - a workflow test: 16 tasks, names, `runs_after`, entry points exist.
  - The notebook-structure test (`tests/workload_foundation/test_jupyter_scripts.py`) covers the new notebooks.
- [x] **Step 6 — AGENTS.md (FR-7)**:
  - naming conventions: notebooks, bronze and silver tables, table locations, workflows, tasks, checkpoints;
  - which Jupyter helpers a notebook includes: Initialization, and for notebooks with task arguments a "Task arguments" section with `TASK_ARGUMENTS`, `WIDGET_LIST` and `jupyter_input_widget_helper.py`;
  - `checkpoint_path` and the `s3ckpt://` scheme;
  - the `tpch` subproject in the layout example.
- [x] **Step 7 — README (FR-8)**: the `tpch` subproject (what it does, the tables, the workflow, the lookback as a temporary workflow edit), `checkpoint_path` in the config section, the naming conventions.
- [x] **Step 8 — Local checks**: `scripts/code_quality.sh all`, `python -m pytest -q`, and the platform validator on the repository. Report results as they are. Code summary in `aidlc-docs/current/construction/tpch/code/summary.md`.

## Not in this stage
Commits and pushes (only with your approval, in Build and Test); UAT runs; the Jupyter check; knowledge documents (at closure).
