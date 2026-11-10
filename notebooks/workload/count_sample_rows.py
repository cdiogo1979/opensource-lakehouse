# %% [markdown]
# # Count rows in the sample Iceberg table
#
# This Jupytext `py:percent` notebook checks the smoke table created by
# `test_environment.py`. It is read-only and logs the selected environment,
# table, and row count.

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
# !lakehouse-install-requirements ~/work/opensource-lakehouse

# %%
# %run ../common/jupyter_environment_resolver.py

# %% [markdown]
# ## Start Spark and load the environment configuration
#
# In Jupyter, the Initialization cells above select `dev` (or
# `LAKEHOUSE_ENVIRONMENT`) and expose `spark` and `config`. In Airflow, `spark-submit` starts the session using the
# environment and config directory passed by the DAG.

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
# ## Count the table rows
#
# The table name is shared with the initializer. The count reads the current
# Iceberg snapshot and does not change table contents.

# %%
SAMPLE_TABLE_NAME = "sample_spark_job_output"


def count_sample_rows(spark: Any, config: Mapping[str, Any]) -> int:
    """Count and log rows in the configured environment's smoke table.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.

    Returns:
        Number of rows in the sample Iceberg table.
    """
    table_identifier = f"{config['database_name']}.{SAMPLE_TABLE_NAME}"
    logger.info("Counting rows in Iceberg table '%s'.", table_identifier)
    row_count = spark.table(table_identifier).count()
    logger.info("Table '%s' contains %d rows.", table_identifier, row_count)
    return row_count


# %% [markdown]
# ## Run the count and stop Spark

# %%
if __name__ == "__main__":
    # Importing this workload from pytest must not start Spark or parse arguments.
    if "ipykernel" not in sys.modules:
        from notebooks.common.job_runtime import start_spark_job

        spark, config = start_spark_job("count_sample_rows")
    logger.info("Environment: %s", config.environment)
    logger.info("Loaded configuration: %s", config.to_dict())
    try:
        count_sample_rows(spark, config)
    finally:
        spark.stop()
