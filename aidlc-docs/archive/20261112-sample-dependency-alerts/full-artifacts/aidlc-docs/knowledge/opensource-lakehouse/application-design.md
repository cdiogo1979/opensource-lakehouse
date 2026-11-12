# Application Design — opensource-lakehouse-sample-dp (repository level)

This repository is a lakehouse **data product repository** for the `opensource-lakehouse-infra` platform. It holds workflow declarations, Spark workloads (Jupytext notebooks), non-secret configuration and tests; the platform builds and runs the DAGs. Subproject design: [`../tpch/application-design.md`](../tpch/application-design.md). This replaces the retired design (Nessie, `DockerOperator`, an in-repository DAG factory, the bundle client). History: the [TPC-H Medallion intent archive](../../archive/20261111-tpch-medallion/intent-summary.md).

## Platform contract
| This repository | The platform (`opensource-lakehouse-infra`) |
|---|---|
| `workflows/<project>/<name>.json` (workflow JSON v1) | The `lakehouse_dags` factory builds `<bundle>-<name>` DAGs from them; Airflow Git bundles `<product>-main` (prod) and `<product>-uat` (uat) |
| `notebooks/workload/<project>/<layer>/*.py` | One Spark container per DAG run, the bundle mounted read-only; `spark-submit` per task |
| `notebooks/common/` helpers | `lakehouse_spark.create_spark_session` (catalogs, token, redaction, checkpoint keys) |
| `configs/<env>.yml`, optional `configs/<product>/<env>.yml` | The writer token per run; Polaris-vended storage credentials; checkpoint keys |
| `dags/lakehouse.py` (fixed stub) | The CI validator `lakehouse-validate-workflows`, the shared Python 3.10 lock |
| `requirements.txt` (pinned extras, e.g. `duckdb==1.5.6`) | Installed per Airflow run and with `lakehouse-install-requirements` in Jupyter |

## Subprojects and layers
- Each subproject has the same folder name under `workflows/` and `notebooks/workload/` (and `aidlc-docs/knowledge/`): today `sample` (notebooks in `other/`) and `tpch` (`bronze/`, `silver/`).
- Notebook layer folders: `bronze/`, `silver/`, `gold/`, `ops/`, `deploy/`, `other/`, one level deep; workflows have no layers. A workflow's `entrypoint` is relative to `notebooks/workload/<project>/` (for example `bronze/bronze_ingestion.py`); full paths are refused.
- DAG IDs don't include the subproject, so workflow names are unique across the repository.

## Naming conventions (AGENTS.md)
- Notebooks `<layer>_<action>.py`; bronze tables `<project>_<entity>_<source>_brz`; silver tables `<project>_<entity>`; table locations `<storage_path>/<catalog_name>/<database_name>/<table>`; workflows `<project>_<purpose>`; tasks `<target_table>_load`; checkpoints `<checkpoint_path>/<project>/<target_table>`.
- All tables of an environment live in its one namespace (`database_name`): products can't create namespaces.
- Materialized views: `materialized_views/<project>/<name>.sql`, named `mv_<project>_<purpose>` (or for an aggregate's dimensions), one `CREATE MATERIALIZED VIEW ${mv_database}.<name>` statement each with `${catalog}.${namespace}.<table>` sources; developed by hand in the dev MV database, deployed to UAT and prod by the platform as the writer.

## Notebook standard
Title cell (purpose, inputs, effects); `## Initialization` (`# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp`, `# %run ../../../common/jupyter_environment_resolver.py`, commented in Airflow); `## Imports`; for task arguments a `## Task arguments` section (`TASK_ARGS_DEFINITION`, the arguments the job accepts, used in Airflow and Jupyter; then `TASK_ARGS_VALUES`, the Jupyter-only values with a working example; each with a comment; no input widgets); the job's own sections; `## Execution` with only the `if __name__ == "__main__":` block, which stops Spark in `finally:`. A test checks the structure.

## Environments
`prod` (bundle `-main`), `uat` (`-uat`), `dev` (Jupyter only). Configs need `storage_path`, `database_name`, usually `catalog_name`, and for streaming jobs `checkpoint_path: s3ckpt://<bucket>/checkpoints`. No secrets anywhere in the repository.

## Operational limits
- A DAG run's tasks share one Spark container: order tasks (`runs_after`) so few Spark jobs run at once (the workflow format has no parallelism limit; platform follow-up).
- A Jupyter server has 2 GiB: one notebook with a Spark session at a time (shut down a kernel before starting another).
- The product writer can't drop tables or create namespaces.
