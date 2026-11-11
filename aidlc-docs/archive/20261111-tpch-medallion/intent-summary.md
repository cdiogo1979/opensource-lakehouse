# Intent Summary: TPC-H Medallion Subproject

## Intent
TPC-H Medallion Subproject (`20261111-tpch-medallion`)

## Objective
A tpch subproject with bronze (DuckDB TPC-H generation into Iceberg) and silver (streaming merge of bronze changes), naming conventions, and the notebook standard with its Jupyter helpers documented in AGENTS.md.

## Date
2026-11-11

## Scope
Included: bronze and silver notebooks, workflow tpch_medallion, configs checkpoint_path, AGENTS.md and README, tests, knowledge for tpch and the repository. Excluded: gold, a production run, an Airflow lookback run; platform changes (done in opensource-lakehouse-infra intents 20261111-spark-s3-checkpoints and 20261111-starrocks-metadata-access).

## Units / workstreams
tpch

## Major requirements
- FR-2 naming: tpch_<entity>_db_brz, tpch_<entity>, locations <storage_path>/<catalog>/<database>/<table>, tasks <target_table>_load, checkpoints <checkpoint_path>/<project>/<target_table>.
- FR-3 bronze append-only with scale_factor and bronze_ingestion_timestamp.
- FR-4 silver streaming availableNow with MERGE_KEYS and silver_lookback_days.
- FR-6 workflow tpch_medallion; FR-7 AGENTS.md conventions and Jupyter helpers.

## Architecture and design decisions
- D2 streaming with s3ckpt:// checkpoints (after the platform intent).
- D3 names defined in each notebook.
- D7 two lanes (CR-3) after OOM in UAT.
- D8 lookback by a temporary workflow edit; platform params later.

## Implementation decisions
- Exact DuckDB types via DESCRIBE, decimals and dates as text.
- No count queries in bronze (user request).
- JSON start records and summaries with environment, bucket, tables, locations and checkpoint.
- Counts per batch ID in foreachBatch.

## Deviations
- Paused at Application Design for the platform intent 20261111-spark-s3-checkpoints (CR-2).
- CR-3 two lanes and retries after the first UAT run.
- The Airflow lookback test was skipped (user); checked in Jupyter.

## Verification
construction/build-and-test/build-and-test-summary.md: code quality clean; tests 112 local (2 DuckDB skips), 21 in the Spark runtime image; Jenkins default_cd SUCCESS on the pull request; UAT default-uat-tpch_medallion 21/21 (7a07ce9); Jupyter bronze and silver with a lookback in dev. Not run: an Airflow lookback, a production run.

## Canonical documents updated
- aidlc-docs/knowledge/tpch/application-design.md
- aidlc-docs/knowledge/tpch/functional-design/medallion-load.md
- aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/jenkins-deployment.md

## Superseded decisions
- Incremental batch reads with a silver snapshot property (first probe) superseded by streaming checkpoints.
- Parallel per-entity tasks superseded by two lanes (CR-3).
- The stale opensource-lakehouse knowledge (Nessie, DockerOperator, in-repository factory) replaced by the current platform contract.

## Archived artifacts
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/functional-design/workload-foundation.md
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/functional-design/jenkins-deployment.md
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/notebooks/workload/tpch/bronze/bronze_ingestion.py
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/notebooks/workload/tpch/silver/silver_processing.py
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/workflows/tpch/tpch_medallion.json
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/configs/dev.yml
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/configs/uat.yml
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/configs/prod.yml
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/AGENTS.md
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/README.md
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/tests/tpch
- aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/tests/workload_foundation/test_config_loader.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-tpch-medallion/full-artifacts/`
