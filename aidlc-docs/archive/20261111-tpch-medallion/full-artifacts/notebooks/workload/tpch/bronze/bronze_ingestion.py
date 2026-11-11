# %% [markdown]
# # TPC-H bronze ingestion
#
# This Jupytext `py:percent` notebook generates one TPC-H entity in memory with
# DuckDB (the `duckdb` package from this repository's `requirements.txt`) and
# appends it to the bronze table `tpch_<entity>_db_brz` of the environment's
# namespace, with the run's `scale_factor` and `bronze_ingestion_timestamp`.
# The first run creates the table at
# `<storage_path>/<catalog_name>/<database_name>/tpch_<entity>_db_brz`; every
# later run appends one batch (bronze is append-only). Column types follow
# DuckDB's exactly (decimals and dates included). Row counts are not checked
# (counting is expensive). It logs one JSON record when it starts (environment,
# bucket, target table and location) and one summary when it ends.
#
# In Airflow, `workflows/tpch/tpch_medallion.json` runs it once per entity with
# `--entity <name>` after `--` (task `tpch_<entity>_db_brz_load`); `--scale-factor`
# is optional (default 0.01). In Jupyter, run the Initialization cells (and
# restart the kernel after the first install); then run the widget cell below,
# fill in `entity` (and, optionally, `scale_factor`), and run the remaining
# cells. DuckDB downloads its `tpch` extension the first time it is used, so the
# first run needs network access.

# %% [markdown]
# ## Initialization
#
# Jupyter only: in `spark-submit` (Airflow) these two cells are comments.
# 1. Install this repository's extra packages (`requirements.txt`). After the
#    first install in a server session, restart the kernel, then run all cells.
# 2. Find this clone, load its config and start Spark: `dev` by default; for
#    another environment, run `%env LAKEHOUSE_ENVIRONMENT=uat` (or `prod`) first.
#    It defines `spark` and `config`.

# %%
# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp

# %%
# %run ../../../common/jupyter_environment_resolver.py

# %% [markdown]
# ## Imports
#
# Standard and third-party imports, and logging. Under `spark-submit` the
# repository root is on `PYTHONPATH`; in Jupyter the Initialization put it there.

# %%
import json
import logging
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# %% [markdown]
# ## Task arguments
#
# The same declaration serves both places: Airflow passes the workflow's `args`
# (`--entity orders`); in Jupyter the input widgets below hold the values (or a
# `TASK_ARGS` list, when there are no widgets). The common parser only reads them;
# this notebook checks them (`check_arguments`).

# %%
TASK_ARGUMENTS = {"entity": {"required": True}, "scale_factor": {"default": "0.01"}}
WIDGET_LIST = ["entity", "scale_factor"]

# %%
# %run ../../../common/jupyter_input_widget_helper.py

# %% [markdown]
# ## TPC-H rules
#
# The entities and scale factors of `sample`'s `generate_tpch.py`: 0.001 to 1,
# at most three decimal places. Generated row counts are not checked here.

# %%
ENTITIES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")
SCALE_STEP = Decimal("0.001")
MIN_SCALE_FACTOR = Decimal("0.001")
MAX_SCALE_FACTOR = Decimal("1")


def parse_scale_factor(text: str) -> Decimal:
    """A TPC-H scale factor from 0.001 to 1 with at most three decimal places.

    Args:
        text: The scale factor as written, for example ``"0.01"``.

    Returns:
        The exact decimal value.

    Raises:
        ValueError: The text is not such a number.
    """
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        value = None
    if value is None or not value.is_finite() or not MIN_SCALE_FACTOR <= value <= MAX_SCALE_FACTOR or value != value.quantize(SCALE_STEP):
        raise ValueError(f"the scale factor must be a number from 0.001 to 1 with at most three decimal places, not {text!r}")
    return value


def check_entity(entity: str) -> str:
    """The entity, when it is one of ``ENTITIES``.

    Raises:
        ValueError: Any other value.
    """
    if entity not in ENTITIES:
        raise ValueError(f"unknown TPC-H entity {entity!r}; expected one of {', '.join(ENTITIES)}")
    return entity


def check_arguments(arguments: dict) -> tuple:
    """The entity and the scale factor from the parsed task arguments, checked.

    Args:
        arguments: The mapping from ``parse_task_args(TASK_ARGUMENTS)``.

    Returns:
        ``(entity, scale_factor)``.

    Raises:
        ValueError: The entity is not a TPC-H entity, or the scale factor breaks ``parse_scale_factor``.
    """
    return check_entity(arguments["entity"]), parse_scale_factor(arguments["scale_factor"])


# %% [markdown]
# ## Names
#
# Bronze tables are `<project>_<entity>_<source>_brz` (`tpch_region_db_brz`;
# source `db`, the DuckDB generator). Every table lives in the environment's one
# namespace, at `<storage_path>/<catalog_name>/<database_name>/<table>`.

# %%
PROJECT = "tpch"
SOURCE = "db"


def bronze_table_name(entity: str) -> str:
    """The bronze table of an entity, ``tpch_<entity>_db_brz``."""
    return f"{PROJECT}_{check_entity(entity)}_{SOURCE}_brz"


def qualified_table(config, table: str) -> str:
    """``<catalog_name>.<database_name>.<table>`` from the environment config."""
    return f"{config['catalog_name']}.{config['database_name']}.{table}"


def table_location(config, table: str) -> str:
    """``<storage_path>/<catalog_name>/<database_name>/<table>``, joined by exactly one ``/``."""
    return "/".join((config["storage_path"].rstrip("/"), config["catalog_name"], config["database_name"], table))


def storage_bucket(path: str) -> str:
    """The bucket of an object-store path such as ``s3a://bucket-default-dev/``."""
    return path.split("://", 1)[-1].split("/", 1)[0]


def targets(config, entity: str) -> dict:
    """Where this run writes: environment, bucket, catalog, database, the bronze table and its location (logged)."""
    table = bronze_table_name(entity)
    return {
        "environment": getattr(config, "environment", None),
        "bucket": storage_bucket(config["storage_path"]),
        "catalog": config["catalog_name"],
        "database": config["database_name"],
        "table": qualified_table(config, table),
        "location": table_location(config, table),
    }


# %% [markdown]
# ## Schema
#
# The Spark columns follow DuckDB's own types (`DESCRIBE`): pandas would turn
# DECIMAL into `double` and DATE into `timestamp`. DuckDB returns decimals and
# dates as text, and Spark casts every column to its type, so values are exact.

# %%
DECIMAL_TYPE = re.compile(r"DECIMAL\((\d+),(\d+)\)")
SIMPLE_TYPES = {"INTEGER": "int", "BIGINT": "bigint", "DATE": "date", "VARCHAR": "string"}
TEXT_TYPES = ("DECIMAL", "DATE")


def spark_type(duckdb_type: str) -> str:
    """The Spark SQL type of a DuckDB column type.

    Raises:
        ValueError: A type outside ``SIMPLE_TYPES`` and ``DECIMAL(p,s)``.
    """
    decimal = DECIMAL_TYPE.fullmatch(duckdb_type)
    if decimal:
        return f"decimal({decimal.group(1)},{decimal.group(2)})"
    if duckdb_type in SIMPLE_TYPES:
        return SIMPLE_TYPES[duckdb_type]
    raise ValueError(f"unsupported DuckDB column type {duckdb_type!r}")


def select_sql(entity: str, columns: list) -> str:
    """The DuckDB query for an entity, with DECIMAL and DATE columns as text.

    Args:
        entity: One of ``ENTITIES``.
        columns: ``(name, duckdb_type)`` pairs from ``DESCRIBE``.
    """
    parts = [f"CAST({name} AS VARCHAR) AS {name}" if duckdb_type.startswith(TEXT_TYPES) else name for name, duckdb_type in columns]
    return f"SELECT {', '.join(parts)} FROM {check_entity(entity)}"  # nosec B608 - entity is one of ENTITIES; names come from DESCRIBE


# %% [markdown]
# ## Generate and write
#
# DuckDB generates the whole dataset in memory and this notebook keeps one entity.
# The first run creates the table at its location; later runs append.


# %%
def generate_entity(entity: str, scale_factor: Decimal) -> tuple:
    """Generate TPC-H at ``scale_factor`` in memory and return one entity's rows.

    Returns:
        ``(columns, frame)``: the ``(name, duckdb_type)`` pairs and a pandas DataFrame of the rows.
    """
    check_entity(entity)
    import duckdb

    with duckdb.connect() as connection:
        connection.execute(f"CALL dbgen(sf={parse_scale_factor(str(scale_factor))})")
        columns = [(row[0], row[1]) for row in connection.execute(f"DESCRIBE {entity}").fetchall()]
        for _, duckdb_type in columns:
            spark_type(duckdb_type)
        frame = connection.execute(select_sql(entity, columns)).fetch_df()
    return columns, frame


def append_bronze(spark, config, entity: str, scale_factor: Decimal, columns: list, frame, started: datetime) -> dict:
    """Append the rows, with ``scale_factor`` and ``bronze_ingestion_timestamp``, to the entity's bronze table.

    Returns:
        ``{"rows_appended", "created"}``; ``rows_appended`` is the generated frame's length (no Spark count).
    """
    from pyspark.sql import functions as F

    target = targets(config, entity)
    table, location = target["table"], target["location"]
    rows = spark.createDataFrame(frame).select(
        *[F.col(name).cast(spark_type(duckdb_type)).alias(name) for name, duckdb_type in columns],
        F.lit(str(scale_factor)).cast("decimal(4,3)").alias("scale_factor"),
        F.lit(started).cast("timestamp").alias("bronze_ingestion_timestamp"),
    )
    created = not spark.catalog.tableExists(table)
    if created:
        rows.writeTo(table).using("iceberg").tableProperty("location", location).create()
    else:
        rows.writeTo(table).append()
    return {"rows_appended": len(frame), "created": created}


def summary(config, entity: str, scale_factor: Decimal, started: datetime, written: dict) -> dict:
    """The run's JSON log record: what was written, and where."""
    return {"layer": "bronze", "entity": entity, "scale_factor": str(scale_factor), "bronze_ingestion_timestamp": started.isoformat(), **targets(config, entity), **written}


def ingest(spark, config, entity: str, scale_factor: Decimal) -> dict:
    """Generate one entity and append it to bronze; logs the targets first, then returns and logs the summary."""
    started = datetime.now(timezone.utc)
    logger.info("Bronze ingestion start: %s", json.dumps({"layer": "bronze", "entity": entity, "scale_factor": str(scale_factor), **targets(config, entity)}, sort_keys=True))
    columns, frame = generate_entity(entity, scale_factor)
    record = summary(config, entity, scale_factor, started, append_bronze(spark, config, entity, scale_factor, columns, frame, started))
    logger.info("Bronze ingestion summary: %s", json.dumps(record, sort_keys=True))
    return record


# %% [markdown]
# ## Execution
#
# Reads the task arguments (the workflow's `args` in Airflow, the widgets in
# Jupyter) and checks them. In Airflow, `start_spark_job` loads the environment's
# config and starts Spark; in Jupyter, the Initialization already defined `spark`
# and `config`. Spark is stopped at the end, also after a failure.

# %%
if __name__ == "__main__":
    # Importing this workload from pytest must not start Spark or parse arguments.
    from notebooks.common.cli import parse_task_args

    try:
        entity, scale_factor = check_arguments(parse_task_args(TASK_ARGUMENTS, prog="bronze_ingestion.py"))
    except ValueError as error:
        if "ipykernel" in sys.modules:
            raise
        print(f"bronze_ingestion.py: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    if "ipykernel" not in sys.modules:
        from notebooks.common.job_runtime import start_spark_job

        spark, config = start_spark_job("bronze_ingestion")
    try:
        ingest(spark, config, entity, scale_factor)
    finally:
        spark.stop()
