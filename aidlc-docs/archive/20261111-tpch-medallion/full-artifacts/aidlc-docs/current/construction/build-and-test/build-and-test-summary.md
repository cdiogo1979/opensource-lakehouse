# Build and Test Summary — TPC-H Medallion Subproject

## Build and code analysis
- No build step (Jupytext notebooks and JSON). `.venv/bin/python -m compileall -q dags notebooks`: pass.
- Code quality (the repository's `scripts/code_quality.sh` checks, run through `.venv/bin/python -m` because the local `.venv` scripts still point at the pre-rename path): Ruff, Black, Flake8 pass; Bandit no issues.
- Platform validator (`PYTHONPATH=<infra>/infra/airflow python3 -m lakehouse_dags.validate .`): `OK: 3 workflow(s)`.

## Unit tests
- Local: 112 passed, 2 skipped (DuckDB not installed in the local `.venv`).
- `tests/tpch` in the Spark runtime image with DuckDB 1.5.6: 21 passed (all entities generated with the mapped types).
- Jenkins `default_cd` on the pull request from `tpch-medallion` into `main`: SUCCESS (user-confirmed), with DuckDB installed.

## UAT (Airflow, `default-uat-tpch_medallion`)
| Run | Commit | Result | Cause and action |
|---|---|---|---|
| `manual__2026-11-11T00:23:38` | `91229a0` | 11 success, 8 failed | All tasks shared one Spark container: eight bronze jobs at once, then six silver; two silver jobs exit 137 (OOM), lineitem bronze a Polaris to RustFS timeout, five silver stalled (run ended by removing its container). CR-3: two lanes, one retry per task |
| `manual__2026-11-11T00:43:46` | `7a07ce9` | region bronze failed twice | RustFS not ready since the memory event (lifecycle recovery timeouts); restarted RustFS (user-approved, infra) |
| `manual__2026-11-11T00:53:34` | `7a07ce9` | **21/21 success** in about 3.5 minutes | One bronze and one silver job at a time |

## Jupyter (user, `joe-developer`, dev)
- Bronze `region`: `tpch_region_db_brz` created, 5 rows, 1 batch.
- Silver `region`: incremental run, rerun, and lookback 1 day: `tpch_region` 5 rows, 5 distinct keys; checkpoint `s3ckpt://bucket-default-dev/checkpoints/tpch/tpch_region` with commits, metadata, offsets, sources.
- First attempt OOM-killed (2 GiB server limit, an older kernel's Spark JVM still alive); works with other kernels shut down.

## Not run
- A lookback in Airflow (user choice: checked in Jupyter only); a production run.

## Platform issues found and handled (opensource-lakehouse-infra)
- StarRocks FE restart lost the runtime LDAP bind pattern; re-applied with `bootstrap-starrocks.py --runtime-only`.
- DBeaver table listings refused (error 5203): fixed by the closed infra intent `20261111-starrocks-metadata-access`.
- Follow-ups recorded in `aidlc-state.md`: per-workflow parallelism limit and per-job Spark memory; automatic LDAP bind-pattern re-apply after an FE restart; Jupyter memory limit above 2G; workflow params (lookback at trigger time).

## Status
All planned checks passed except the two listed under "Not run".
