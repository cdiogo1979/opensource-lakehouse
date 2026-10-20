"""Idempotently initialize the configured Spark catalog namespace.

After initialization, this job writes a small synthetic smoke table to the
dedicated ``sample_spark_job_output`` child location. Object storage prefixes
are created by the table write; no Hadoop S3A filesystem operation is needed.
"""

import sys
from pathlib import Path
from typing import Any

try:
    from config_loader import EnvironmentConfig, load_environment_config
    from cli import parse_args
except ModuleNotFoundError:
    # Supports direct execution and spark-submit runs with shared helpers.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from config_loader import EnvironmentConfig, load_environment_config
    from cli import parse_args


SAMPLE_TABLE_NAME = "sample_spark_job_output"
SAMPLE_ROWS = (
    ("sample-001", "alpha", 1),
    ("sample-002", "beta", 2),
)
SAMPLE_SCHEMA = "record_id STRING, category STRING, quantity INT"


def create_namespace(spark: Any, config: EnvironmentConfig) -> None:
    """Create the configured catalog namespace if it does not exist.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.

    Raises:
        Exception: Propagates catalog errors.
    """
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {config['database_name']}")


def write_sample_dataset(spark: Any, config: EnvironmentConfig) -> None:
    """Overwrite the dedicated sample table at its environment child path.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.

    Raises:
        Exception: Propagates Spark table or storage write failures.
    """
    output_path = f"{config['storage_path']}{SAMPLE_TABLE_NAME}"
    table_identifier = f"{config['database_name']}.{SAMPLE_TABLE_NAME}"
    dataframe = spark.createDataFrame(SAMPLE_ROWS, schema=SAMPLE_SCHEMA)
    (dataframe.write.mode("overwrite").option("path", output_path).saveAsTable(table_identifier))


def initialize_environment(spark: Any, config: EnvironmentConfig) -> None:
    """Initialize the catalog namespace and run the smoke table write.

    Args:
        spark: Active SparkSession-compatible object.
        config: Validated settings for the explicitly selected environment.

    Raises:
        Exception: Propagates catalog and Spark write failures.
    """
    create_namespace(spark, config)
    write_sample_dataset(spark, config)


def main(argv: Any = None) -> None:
    """Load the selected config and run environment initialization.

    Args:
        argv: Optional argument list, primarily for direct invocation.
    """
    args = parse_args(argv)
    from pyspark.sql import SparkSession
    from pyspark import SparkFiles

    spark = SparkSession.builder.appName(f"{args.environment}-init_environment").getOrCreate()
    try:
        config_dir = args.config_dir
        if config_dir == "spark-files":
            config_dir = SparkFiles.getRootDirectory()
        config = load_environment_config(args.environment, config_dir)
        initialize_environment(spark, config)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
