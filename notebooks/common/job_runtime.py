"""Shared startup helpers for Jupyter and spark-submit workloads."""

import os
import sys
from argparse import Namespace
from typing import Any

from .cli import parse_args
from .config_loader import EnvironmentConfig, load_environment_config


def start_spark_job(app_name: str, argv: Any = None) -> tuple[Any, EnvironmentConfig]:
    """Load environment settings and start a Spark session.

    In Jupyter, select the environment with ``LAKEHOUSE_ENVIRONMENT`` and
    optionally override the config directory with ``LAKEHOUSE_CONFIG_DIR``.
    In spark-submit, parse the shared ``--environment`` and ``--config-dir``
    arguments.

    Args:
        app_name: Spark application name to display in the Spark UI.
        argv: Optional command-line arguments for direct invocation.

    Returns:
        The started Spark session and validated environment configuration.
    """
    if "ipykernel" in sys.modules:
        args = Namespace(
            environment=os.environ.get("LAKEHOUSE_ENVIRONMENT", "dev"),
            config_dir=os.environ.get("LAKEHOUSE_CONFIG_DIR"),
        )
    else:
        args = parse_args(argv)

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName(f"{args.environment}-{app_name}").getOrCreate()
    try:
        config_dir = args.config_dir
        if config_dir == "spark-files":
            from pyspark import SparkFiles

            config_dir = SparkFiles.getRootDirectory()

        config = load_environment_config(args.environment, config_dir)
    except Exception:
        spark.stop()
        raise

    return spark, config
