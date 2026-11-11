# Deployment Instructions — tpch subproject

All steps are manual. UAT is already deployed (`uat` at `7a07ce9`, run 21/21).

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | Merge the pull request `tpch-medallion` into `main` | `default_cd` green (done); review | GitHub: merge | `main` contains `91229a0`, `7a07ce9`, `fe272d9` | Revert the merge commit |
| 2 | Production bundle picks up the change | Step 1; Airflow running | Wait up to 5 minutes (bundle refresh) | DAG `default-main-tpch_medallion` listed, no import errors | Import error: the message names the workflow problem; fix on a branch |
| 3 | First production run | Step 2; prod checkpoint key staged (`bucket-default`, platform) | Airflow UI: trigger `default-main-tpch_medallion` | 21/21 tasks; tables `lakehouse.default_lh.tpch_<entity>_db_brz` and `tpch_<entity>` created | A failed task retries once; check the run log's JSON start record (bucket, tables, checkpoint) and the platform health (RustFS, Polaris) |
| 4 | Optional cleanup of UAT probes | — | — | The first UAT run left partial silver tables; later runs merged them correctly, so nothing is required | — |

Rollback: revert the commits on `main`; created tables stay (the writer can't drop them; an owner or the platform team can).
