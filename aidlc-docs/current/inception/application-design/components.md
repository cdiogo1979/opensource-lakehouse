# Components — TPC-H Medallion Subproject

One unit, `tpch`.

| ID | Component | Path | Status |
|---|---|---|---|
| C1 | Bronze ingestion notebook | `notebooks/workload/tpch/bronze/bronze_ingestion.py` | New |
| C2 | Silver processing notebook | `notebooks/workload/tpch/silver/silver_processing.py` | New |
| C4 | Workflow | `workflows/tpch/tpch_medallion.json` | New |
| C5 | Environment configs | `configs/{dev,uat,prod}.yml` | Changed: `checkpoint_path` |
| C6 | Shared helpers | `notebooks/common/{job_runtime,cli,config_loader,jupyter_environment_resolver,jupyter_input_widget_helper}.py` | Used unchanged |
| C7 | Docs and tests | `AGENTS.md`, `README.md`, `tests/tpch/`, the notebook-structure test | Changed or new |

## Responsibilities
- **C1** generates one TPC-H entity in memory with DuckDB (its own copy of the generator, Q4 C) and appends it, with `scale_factor` and `bronze_ingestion_timestamp`, to `tpch_<entity>_db_brz`, creating the table at its FR-2 location when missing. Logs one JSON summary.
- **C2** streams the bronze table's appended snapshots (`trigger(availableNow=True)`) from its checkpoint `<checkpoint_path>/tpch/tpch_<entity>`, and per micro-batch merges the latest row per merge key into `tpch_<entity>`, creating it when missing. With `silver_lookback_days > 0` it first deletes this entity's checkpoint and starts from that many days ago. Logs one JSON summary.
- **Naming** (D3): each notebook defines its own names from the config: the qualified name `<catalog_name>.<database_name>.<table>`, the location `<storage_path>/<catalog_name>/<database_name>/<table>`, and (silver) the checkpoint `<checkpoint_path>/tpch/<table>`. There is no shared naming module; AGENTS.md documents the conventions.
- **C4** declares `tpch_medallion`: 16 tasks, `tpch_<entity>_db_brz_load` then `tpch_<entity>_load`; no lookback argument (D8: a lookback is a temporary edit).
- **C5** adds `checkpoint_path: s3ckpt://<bucket>/checkpoints` per environment.
- **C6** is reused as every notebook uses it: `start_spark_job`, `parse_task_args` with `TASK_ARGUMENTS` and `WIDGET_LIST`, the Jupyter resolver and widget helper.
- **C7** documents the naming conventions and the notebook helpers in AGENTS.md (FR-7), the subproject in the README, and tests the pure rules (FR-8).

## Interfaces
- **Task arguments**: C1 `--entity` (required), `--scale-factor` (default `0.01`); C2 `--entity` (required), `--silver-lookback-days` (default `0`). Widgets in Jupyter carry the same names.
- **Tables**: bronze `tpch_<entity>_db_brz` (entity columns plus `scale_factor`, `bronze_ingestion_timestamp`) → silver `tpch_<entity>` (the same columns).
- **Config keys used**: `storage_path`, `catalog_name`, `database_name`, `checkpoint_path`.
