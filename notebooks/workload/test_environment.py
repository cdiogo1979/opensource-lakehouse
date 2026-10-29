# %% [markdown]
# # Initialize the lakehouse environment
#
# This file uses Jupytext's `py:percent` format. Markdown cells explain the
# workflow when opened as a notebook, and the Python file remains runnable
# with `spark-submit`. The job creates a namespace if needed and overwrites
# only its dedicated synthetic smoke table.

# %% [markdown]
# ## Imports
#
# Jupyter startup is delegated to `jupyter_helper.py` below. In a regular
# `spark-submit` run, the DAG supplies the repository root on `PYTHONPATH`.

# %%
import logging
import sys
from collections.abc import Mapping
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# %% [markdown]
# ## Select the environment and start Spark
#
# In a Jupyter kernel, set `LAKEHOUSE_ENVIRONMENT` to `dev`, `uat`, or `prod`
# before running the helper; it presets `dev`. The `%run` line is a Jupytext
# magic: it becomes active in Jupyter and remains a comment in this Python
# script, so Spark-submit skips it.

# %%
# %run ./jupyter_helper.py

# %% [markdown]
# ## Workload settings and operations
#
# `storage_path` is expected to end in `/`, and `database_name` is a clean
# Spark identifier. The sample write is deterministic and scoped to the
# `sample_spark_job_output` Iceberg table, with a `creation_timestamp` column.

# %%
SAMPLE_TABLE_NAME = "sample_spark_job_output"
SAMPLE_ROWS = (
    ("sample-001", "alpha", 1),
    ("sample-002", "beta", 2),
)
SAMPLE_SCHEMA = "record_id STRING, category STRING, quantity INT"


def write_sample_dataset(spark: Any, config: Mapping[str, Any]) -> None:
    """Overwrite the dedicated sample table at its environment child path.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.
    """
    storage_path = config["storage_path"].rstrip("/")
    output_path = f"{storage_path}/{config['catalog_name']}/{config['database_name']}/{SAMPLE_TABLE_NAME}"
    table_identifier = f"{config['database_name']}.{SAMPLE_TABLE_NAME}"
    if spark.catalog.tableExists(table_identifier):
        logger.info(
            "Table '%s' exists; replacing its current contents with a new Iceberg snapshot.",
            table_identifier,
        )
    else:
        logger.info("Table '%s' does not exist; creating a new Iceberg table.", table_identifier)

    from pyspark.sql.functions import current_timestamp

    dataframe = spark.createDataFrame(SAMPLE_ROWS, schema=SAMPLE_SCHEMA)
    dataframe = dataframe.withColumn("creation_timestamp", current_timestamp())
    (dataframe.write.format("iceberg").mode("overwrite").option("path", output_path).saveAsTable(table_identifier))
    logger.info(
        "Committed current contents to Iceberg table '%s' at '%s'; Nessie GC manages " "physical cleanup of files no longer referenced by any branch or tag.",
        table_identifier,
        output_path,
    )


def test_environment(spark: Any, config: Mapping[str, Any]) -> None:
    """Write its synthetic smoke table.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.
    """
    write_sample_dataset(spark, config)


# %% [markdown]
# ## Create the namespace and smoke table, then stop Spark
#
# The table write creates the object-storage prefix. Only the dedicated
# `sample_spark_job_output` table is overwritten. The `finally` block stops
# Spark even if catalog or storage initialization fails.

# %%
if __name__ == "__main__":
    # Importing this workload from pytest or another module must not start
    # Spark or parse the caller's command-line arguments. In Jupyter, the
    # preceding %run magic supplies `spark` and `config` in this namespace.
    if "ipykernel" not in sys.modules:
        from notebooks.common.job_runtime import start_spark_job

        spark, config = start_spark_job("test_environment")

    logger.info("Environment: %s", config.environment)
    logger.info("Loaded configuration: %s", config.to_dict())
    try:
        test_environment(spark, config)
    finally:
        spark.stop()
