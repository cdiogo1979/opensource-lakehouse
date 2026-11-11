# %% [markdown]
# # TPC-H silver processing
#
# This Jupytext `py:percent` notebook merges the changes of one TPC-H entity's
# bronze table `tpch_<entity>_db_brz` into its silver table `tpch_<entity>`,
# which keeps one row per merge key (`MERGE_KEYS`): the newest by
# `bronze_ingestion_timestamp`. Changes come from Spark Structured Streaming on
# the bronze Iceberg table (`trigger(availableNow=True)`): each run processes the
# bronze snapshots appended since the last run, remembered in the checkpoint
# `<checkpoint_path>/tpch/tpch_<entity>` (`checkpoint_path` from the environment
# config, an `s3ckpt://` path). The first run creates the silver table at
# `<storage_path>/<catalog_name>/<database_name>/tpch_<entity>`. A silver row is
# replaced only by a newer bronze row, so any replay is safe. It logs one JSON
# record when it starts (environment, bucket, source and target tables with their
# locations, checkpoint) and one summary when it ends.
#
# `silver_lookback_days` (default 0) reprocesses history: with N > 0 the run
# deletes this entity's checkpoint and streams the bronze snapshots committed in
# the last N days, then continues from there in later runs.
#
# In Airflow, `workflows/tpch/tpch_medallion.json` runs it once per entity with
# `--entity <name>` (task `tpch_<entity>_load`, after its bronze task). For a
# lookback in uat or prod, temporarily add `--silver-lookback-days <N>` to the
# silver tasks' `args`, push, run, and revert. In Jupyter, run the Initialization
# cells, then set `entity` (and, optionally, `silver_lookback_days`) in
# `TASK_ARGS_VALUES` under Task arguments, and run the remaining cells.

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
# Standard imports and logging. Under `spark-submit` the repository root is on
# `PYTHONPATH`; in Jupyter the Initialization put it there.

# %%
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# %% [markdown]
# ## Task arguments
#
# Two parts: the definition (which arguments the job accepts), used everywhere,
# and the values for a Jupyter run. In Airflow the values come from the
# workflow's `args` (`--entity orders`) instead. The common parser only reads
# them; this notebook checks them (`check_arguments`).

# %%
# The arguments this job accepts, in Airflow and in Jupyter: each name, and
# whether it is required or its default.
TASK_ARGS_DEFINITION = {"entity": {"required": True}, "silver_lookback_days": {"default": "0"}}

# Jupyter only: this run's values, as strings (a name left out takes its
# default). Airflow ignores it and uses the workflow's `args`.
TASK_ARGS_VALUES = {"entity": "region", "silver_lookback_days": "0"}

# %% [markdown]
# ## Merge keys and argument rules
#
# One merge key per entity (two for `partsupp` and `lineitem`). The lookback is a
# whole number of days, 0 to 3650, written in digits.

# %%
MERGE_KEYS = {
    "region": ("r_regionkey",),
    "nation": ("n_nationkey",),
    "supplier": ("s_suppkey",),
    "customer": ("c_custkey",),
    "part": ("p_partkey",),
    "partsupp": ("ps_partkey", "ps_suppkey"),
    "orders": ("o_orderkey",),
    "lineitem": ("l_orderkey", "l_linenumber"),
}
MAX_LOOKBACK_DAYS = 3650
LOOKBACK_TEXT = re.compile(r"0|[1-9][0-9]{0,3}")
DAY_MS = 86_400_000


def check_entity(entity: str) -> str:
    """The entity, when it is a key of ``MERGE_KEYS``.

    Raises:
        ValueError: Any other value.
    """
    if entity not in MERGE_KEYS:
        raise ValueError(f"unknown TPC-H entity {entity!r}; expected one of {', '.join(MERGE_KEYS)}")
    return entity


def parse_lookback_days(text: str) -> int:
    """The lookback in days, from ``"0"`` to ``"3650"`` written in digits.

    Raises:
        ValueError: Any other text.
    """
    if not isinstance(text, str) or not LOOKBACK_TEXT.fullmatch(text) or int(text) > MAX_LOOKBACK_DAYS:
        raise ValueError(f"silver_lookback_days must be a whole number of days from 0 to {MAX_LOOKBACK_DAYS}, not {text!r}")
    return int(text)


def check_arguments(arguments: dict) -> tuple:
    """The entity and the lookback from the parsed task arguments.

    Args:
        arguments: The mapping from ``parse_task_args(TASK_ARGS_DEFINITION)``.

    Returns:
        ``(entity, lookback_days)``.

    Raises:
        ValueError: An unknown entity, or a lookback outside ``parse_lookback_days``.
    """
    return check_entity(arguments["entity"]), parse_lookback_days(arguments["silver_lookback_days"])


# %% [markdown]
# ## Names
#
# Silver tables are `<project>_<entity>` (`tpch_region`); their bronze source is
# `<project>_<entity>_db_brz`. Every table lives in the environment's one
# namespace, at `<storage_path>/<catalog_name>/<database_name>/<table>`; the
# checkpoint is `<checkpoint_path>/<project>/<table>`.

# %%
PROJECT = "tpch"
CHECKPOINT_SCHEME = "s3ckpt://"


def silver_table_name(entity: str) -> str:
    """The silver table of an entity, ``tpch_<entity>``."""
    return f"{PROJECT}_{check_entity(entity)}"


def bronze_table_name(entity: str) -> str:
    """The bronze table of an entity, ``tpch_<entity>_db_brz``."""
    return f"{PROJECT}_{check_entity(entity)}_db_brz"


def qualified_table(config, table: str) -> str:
    """``<catalog_name>.<database_name>.<table>`` from the environment config."""
    return f"{config['catalog_name']}.{config['database_name']}.{table}"


def table_location(config, table: str) -> str:
    """``<storage_path>/<catalog_name>/<database_name>/<table>``, joined by exactly one ``/``."""
    return "/".join((config["storage_path"].rstrip("/"), config["catalog_name"], config["database_name"], table))


def checkpoint_location(config, table: str) -> str:
    """``<checkpoint_path>/tpch/<table>``.

    Raises:
        ValueError: ``checkpoint_path`` is missing, empty, or not an ``s3ckpt://`` path.
    """
    base = config.get("checkpoint_path")
    if not isinstance(base, str) or not base.startswith(CHECKPOINT_SCHEME) or len(base.rstrip("/")) <= len(CHECKPOINT_SCHEME):
        raise ValueError(f"the environment config needs checkpoint_path, an {CHECKPOINT_SCHEME} path in the product's bucket, not {base!r}")
    return "/".join((base.rstrip("/"), PROJECT, table))


def storage_bucket(path: str) -> str:
    """The bucket of an object-store path such as ``s3a://bucket-default-dev/``."""
    return path.split("://", 1)[-1].split("/", 1)[0]


def targets(config, entity: str) -> dict:
    """What this run reads and writes (logged): environment, bucket, catalog, database, source, target and checkpoint."""
    source, target = bronze_table_name(entity), silver_table_name(entity)
    checkpoint = checkpoint_location(config, target)
    return {
        "environment": getattr(config, "environment", None),
        "bucket": storage_bucket(config["storage_path"]),
        "catalog": config["catalog_name"],
        "database": config["database_name"],
        "source": qualified_table(config, source),
        "source_location": table_location(config, source),
        "table": qualified_table(config, target),
        "location": table_location(config, target),
        "checkpoint": checkpoint,
        "checkpoint_bucket": storage_bucket(checkpoint),
    }


# %% [markdown]
# ## Merge rules
#
# Each micro-batch keeps the newest bronze row per key, then merges it: new keys
# are inserted, and an existing row is updated only by a strictly newer bronze row.


# %%
def merge_condition(keys: tuple) -> str:
    """``t.<key> = s.<key>`` for every key, joined by ``AND``."""
    return " AND ".join(f"t.{key} = s.{key}" for key in keys)


def merge_sql(target: str, view: str, keys: tuple) -> str:
    """The ``MERGE INTO`` statement of one micro-batch."""
    update = "WHEN MATCHED AND s.bronze_ingestion_timestamp > t.bronze_ingestion_timestamp THEN UPDATE SET *"
    return f"MERGE INTO {target} t USING {view} s ON {merge_condition(keys)} {update} WHEN NOT MATCHED THEN INSERT *"


def latest_per_key(batch, keys: tuple):
    """The batch's newest row per key, by ``bronze_ingestion_timestamp``."""
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    newest_first = Window.partitionBy(*keys).orderBy(F.col("bronze_ingestion_timestamp").desc())
    return batch.withColumn("_rank", F.row_number().over(newest_first)).filter(F.col("_rank") == 1).drop("_rank")


# %% [markdown]
# ## Stream
#
# Counts are taken inside each micro-batch, once per batch ID, because the outer
# session may hold a cached version of a table it created. A lookback deletes
# exactly this entity's checkpoint before the stream starts.


# %%
def start_timestamp_ms(lookback_days: int, now: datetime) -> int:
    """``now`` minus ``lookback_days`` days, in epoch milliseconds (Iceberg's ``stream-from-timestamp``)."""
    return int(now.timestamp() * 1000) - lookback_days * DAY_MS


def reset_checkpoint(spark, config, entity: str) -> bool:
    """Delete this entity's checkpoint folder (recursively), and nothing else; returns whether one existed."""
    location = checkpoint_location(config, silver_table_name(entity))
    path = spark._jvm.org.apache.hadoop.fs.Path(location)
    filesystem = path.getFileSystem(spark._jsc.hadoopConfiguration())
    existed = filesystem.exists(path)
    if existed:
        filesystem.delete(path, True)
    return bool(existed)


def run_stream(spark, config, entity: str, checkpoint: str, stream_from_ms) -> dict:
    """Stream the entity's new bronze snapshots into silver; returns the batch counts."""
    keys = MERGE_KEYS[entity]
    source = qualified_table(config, bronze_table_name(entity))
    target = qualified_table(config, silver_table_name(entity))
    location = table_location(config, silver_table_name(entity))
    view = f"{PROJECT}_{entity}_updates"
    counts = {}

    def merge_batch(batch, batch_id):
        batch.persist()
        try:
            latest = latest_per_key(batch, keys)
            session = batch.sparkSession
            if not session.catalog.tableExists(target):
                latest.limit(0).writeTo(target).using("iceberg").tableProperty("location", location).create()
            latest.createOrReplaceTempView(view)
            session.sql(merge_sql(target, view, keys))
            counts[batch_id] = (batch.count(), latest.count())
        finally:
            batch.unpersist()

    reader = spark.readStream.format("iceberg")
    if stream_from_ms is not None:
        reader = reader.option("stream-from-timestamp", str(stream_from_ms))
    query = reader.load(source).writeStream.foreachBatch(merge_batch).option("checkpointLocation", checkpoint).trigger(availableNow=True).start()
    query.awaitTermination()
    return {
        "batches": len(counts),
        "rows_read": sum(read for read, _ in counts.values()),
        "rows_merged": sum(merged for _, merged in counts.values()),
    }


def process(spark, config, entity: str, lookback_days: int) -> dict:
    """Merge the entity's bronze changes into silver, resetting the checkpoint for a lookback; logs and returns the summary."""
    started = datetime.now(timezone.utc)
    target = targets(config, entity)
    checkpoint = target["checkpoint"]
    logger.info("Silver processing start: %s", json.dumps({"layer": "silver", "entity": entity, "lookback_days": lookback_days, **target}, sort_keys=True))
    stream_from_ms, reset = None, False
    if lookback_days > 0:
        reset = reset_checkpoint(spark, config, entity)
        stream_from_ms = start_timestamp_ms(lookback_days, started)
    counts = run_stream(spark, config, entity, checkpoint, stream_from_ms)
    record = {
        "layer": "silver",
        "entity": entity,
        "lookback_days": lookback_days,
        "stream_from": (started - timedelta(days=lookback_days)).isoformat() if lookback_days > 0 else None,
        "checkpoint_reset": reset,
        **target,
        **counts,
    }
    logger.info("Silver processing summary: %s", json.dumps(record, sort_keys=True))
    return record


# %% [markdown]
# ## Execution
#
# Reads the task arguments (the workflow's `args` in Airflow, `TASK_ARGS_VALUES` in
# Jupyter) and checks them. In Airflow, `start_spark_job` loads the environment's
# config and starts Spark; in Jupyter, the Initialization already defined `spark`
# and `config`. Spark is stopped at the end, also after a failure.

# %%
if __name__ == "__main__":
    # Importing this workload from pytest must not start Spark or parse arguments.
    from notebooks.common.cli import parse_task_args

    try:
        entity, lookback_days = check_arguments(parse_task_args(TASK_ARGS_DEFINITION, prog="silver_processing.py"))
    except ValueError as error:
        if "ipykernel" in sys.modules:
            raise
        print(f"silver_processing.py: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    if "ipykernel" not in sys.modules:
        from notebooks.common.job_runtime import start_spark_job

        spark, config = start_spark_job("silver_processing")
    try:
        process(spark, config, entity, lookback_days)
    finally:
        spark.stop()
