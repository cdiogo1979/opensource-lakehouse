# %% [markdown]
# # Initialize the lakehouse environment
#
# This file uses Jupytext's `py:percent` format. Markdown cells explain the
# workflow when opened as a notebook, and the Python file remains runnable
# with `spark-submit`. The job creates a namespace if needed and overwrites
# only its dedicated synthetic smoke table.

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
# %run ../../common/jupyter_environment_resolver.py

# %% [markdown]
# ## Imports
#
# Standard and third-party imports, and logging. Under `spark-submit` the
# repository root is on `PYTHONPATH`; in Jupyter the Initialization put it there.

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
# ## Sample table
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
        "Committed current contents to Iceberg table '%s' at '%s'; files of replaced snapshots stay until the table's snapshots are expired.",
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
# ## Execution
#
# In Airflow, `start_spark_job` loads the environment's config and starts Spark;
# in Jupyter, the Initialization already defined `spark` and `config`. The table
# write creates the object-storage prefix; only the dedicated
# `sample_spark_job_output` table is overwritten. The `finally` block stops
# Spark even if catalog or storage initialization fails.

# %%
if __name__ == "__main__":
    # Importing this workload from pytest or another module must not start
    # Spark or parse the caller's command-line arguments.
    if "ipykernel" not in sys.modules:
        from notebooks.common.job_runtime import start_spark_job

        spark, config = start_spark_job("test_environment")

    logger.info("Environment: %s", config.environment)
    logger.info("Loaded configuration: %s", config.to_dict())
    try:
        test_environment(spark, config)
    finally:
        spark.stop()
