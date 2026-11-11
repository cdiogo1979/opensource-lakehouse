# Focused Reverse Engineering — TPC-H Medallion Subproject

Intent `20261111-tpch-medallion`. Scope: what a new `tpch` subproject with bronze and silver notebooks builds on. Captured 2026-11-11 at `8b322d2` (`main`).

## Repository today
- **Layout** (AGENTS.md): `workflows/<project>/<name>.json`; notebooks in `notebooks/workload/<project>/<layer>/` with layers `bronze`, `silver`, `gold`, `ops`, `deploy`, `other`; shared code in `notebooks/common/`; knowledge per subproject in `aidlc-docs/knowledge/<project>/`.
- **One subproject**, `sample`: `workflows/sample/{test_environment,generate_tpch}.json`; `notebooks/workload/sample/other/{test_environment,count_sample_rows,generate_tpch}.py`.
- **Notebook structure** (enforced by `tests/workload_foundation/test_jupyter_scripts.py`): title cell; `## Initialization` (`# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp`, `# %run ../../../common/jupyter_environment_resolver.py`); `## Imports`; the job's own sections (settings and functions only); `## Execution` (only the `if __name__ == "__main__":` block).
- **Helpers** (`notebooks/common/`): `job_runtime.start_spark_job` (config, then the platform's Spark session); `cli.parse_task_args` (declared task arguments; widgets or `TASK_ARGS` in Jupyter); `jupyter_environment_resolver.py` and `jupyter_input_widget_helper.py` (`%run`); `config_loader`.
- **TPC-H today**: `sample/other/generate_tpch.py` generates TPC-H in memory with DuckDB (`duckdb==1.5.6` in `requirements.txt`), counts one entity, checks the count against the TPC-H rules, writes nothing. Functions: `parse_scale_factor`, `expected_count`, `check_count`, `generate_tpch`, `check_arguments`; constants `ENTITIES`, `BASE_COUNTS`.
- **Tables today**: `sample_spark_job_output` in the environment's database (`default_lhdev`, `default_lhuat`, `default_lh`), written by `test_environment.py` with `saveAsTable` (Iceberg). No naming convention is documented for tables or workflows beyond "unique workflow names" and "names that make clear which notebook and settings a workflow uses".
- **Configs**: `configs/<env>.yml` with `storage_path`, `catalog_name`, `database_name`; free-form extra keys reach jobs.

## Platform constraints (from the lakehouse platform's canonical design)
- **One namespace per environment**: products have exactly `default_lh` (prod), `default_lhuat`, `default_lhdev`; product roles are never granted `NAMESPACE_CREATE`. Bronze and silver tables therefore share the namespace; the layer has to be part of the table name.
- **Writer privileges** on the namespace: `TABLE_CREATE`, `TABLE_WRITE_PROPERTIES`, `TABLE_WRITE_DATA` (no table drop).
- **Spark**: Spark 3.5.5, Iceberg 1.10.2 with the SQL extensions on every session, so `MERGE INTO` and the Iceberg `create_changelog_view` procedure (Iceberg CDC between snapshots) are available; whether the procedure works through Polaris with vended credentials is to be probed.
- **Runs**: one Spark container per DAG run (`local[*]`), tasks in `runs_after` order; DAG IDs `<bundle>-<name>`; entry points `<layer>/<file>.py`.
- **Jupyter**: developers write only in `dev`; `uat`/`prod` are read-only for them.

## Gaps found
- **Knowledge out of date**: `aidlc-docs/knowledge/opensource-lakehouse/` (application design and two functional designs) still describes Nessie, `DockerOperator`, a repository DAG factory and `lakehouse-*` bundles, all superseded; and its folder isn't a subproject name.
- **Archive missing**: `aidlc-state.md` and `audit.md` point to `aidlc-docs/archive/20261020-lakehouse-workload-foundation`, which commit `8b322d2` removed.
- **Skill wording**: this repository's skill expects the code-quality script from `cicd/Jenkinsfile`; the CI file is `Jenkinsfile` at the root (the script is the same, `scripts/code_quality.sh`).
