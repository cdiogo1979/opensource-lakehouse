# Application Design — TPC-H Medallion Subproject

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md) and [component-dependency.md](component-dependency.md). Requirements: [requirements.md](../requirements/requirements.md) (FR-1 to FR-8, CR-1, CR-2).

## Summary
A `tpch` subproject with two notebooks and one workflow:
- `bronze/bronze_ingestion.py` appends one TPC-H entity, generated in memory with DuckDB, to `tpch_<entity>_db_brz`;
- `silver/silver_processing.py` streams that table's new snapshots and merges the latest row per key into `tpch_<entity>`;
- `workflows/tpch/tpch_medallion.json` runs both for the eight entities (16 tasks).

Each notebook builds its own names and locations from the environment config.

## Decisions
| # | Decision | Reason |
|---|---|---|
| D1 | Bronze is append-only; each run adds a batch with `scale_factor` and `bronze_ingestion_timestamp` | Q2 A; bronze changes are inserts, so silver's CDC is the stream of appended snapshots |
| D2 | Silver uses Spark Structured Streaming on the bronze Iceberg table, `trigger(availableNow=True)`, `foreachBatch` `MERGE INTO` | Q5 (the user's choice, streaming checkpoints); proven on the new platform |
| D3 | Each notebook defines its names: table name pattern, qualified name, table location and (silver) checkpoint location, from the config; no shared naming module | User decision: "names defined on the notebook". The FR-2 conventions are documented in AGENTS.md so each subproject applies them the same way |
| D4 | Tables are created by the notebooks when missing, at the explicit FR-2 location | Writers can create but not drop tables; the location keeps each table in the product's namespace folder |
| D5 | Lookback: `silver_lookback_days = N > 0` deletes this entity's checkpoint, then starts the stream with `stream-from-timestamp = now - N days`; the replay is idempotent because MERGE updates only when the bronze row is newer | FR-4; probed |
| D6 | Silver counts merged rows inside `foreachBatch`, once per batch ID, and reads the silver table only after a refresh | The probe showed the outer session caches a table it created (it read the empty version), and `recentProgress` repeats batch entries |
| D7 | One task per entity per layer, `runs_after` only within an entity | Q3 B; entities fail and rerun independently |
| D8 | The workflow passes no lookback. A lookback in uat or prod is a temporary edit of `tpch_medallion.json` (add `--silver-lookback-days N` to the silver tasks, push, run, revert); in dev, the Jupyter widget | User decision: "temporary edit". The platform doesn't template task arguments; repairs are rare. Airflow Params were considered: workflow JSON v1 has no `params` field and the platform never templates `args`, so they need a platform change (follow-up below) |

## Probe evidence (`audit.md`)
| Probe | Result |
|---|---|
| First (2026-11-11, before the pause) | Table creation at an explicit location, appends, MERGE latest-per-key, DuckDB to Spark: OK. Checkpoints: impossible on the old platform, which led to the platform intent |
| Second (after the platform intent, dev, writer, `lakehouse_spark` settings) | Bronze created at the `s3a://` location from `dev.yml`. Stream run 1: first snapshot; run 2: only the new snapshot; run 3: nothing; after deleting the checkpoint, `stream-from-timestamp` one day back replayed all bronze rows; run 5: resumed. Silver ended correct (key 1 updated, key 4 inserted, 4 rows from 5 bronze rows). The replay wrote one more silver snapshot with unchanged values (copy-on-write rewrite) |

Both probe tables were dropped through the Polaris admin API (204, then 404); their data files stay in the bucket (no purge), as for the first probe.

## Accepted limits
- A lookback replay rewrites the matched silver files once (a new snapshot, same values). Filtering unchanged rows before MERGE is a later optimization.
- Streams fail on bronze snapshots that delete or overwrite data; bronze is append-only, so none are expected. A manual bronze rewrite needs `streaming-skip-*` options or a silver reset.
- Created tables can't be dropped by the writer; a schema mistake needs an owner or the Polaris administrator.
- A dev notebook run and any other dev run share the entity's checkpoint (dev is a sandbox).

## Follow-ups
- **Platform: workflow params** (infra, its own small intent): declare typed params with defaults and limits in workflow JSON, and insert the run's validated values into task `args` at run time without templating. Airflow's "Trigger DAG w/ config" form would then set `silver_lookback_days`; only `tpch_medallion.json` changes here.

## Canonical knowledge (unchanged inventory)
CREATE `knowledge/tpch/application-design.md` and `knowledge/tpch/functional-design/medallion-load.md`; UPDATE the three `knowledge/opensource-lakehouse` documents (naming conventions, the shared helpers, CI).

## Extension compliance (Application Design)
- **PBT (partial)**: properties apply from Functional Design: naming patterns and locations in each notebook; `latest_per_key` picks the newest row per key and is order-independent; merge idempotence (a replay never changes a row to an older one); argument validation. N/A at this stage.
- **Security Baseline, Resiliency**: disabled (Q7).
