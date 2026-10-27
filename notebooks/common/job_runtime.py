"""Shared startup helpers for Jupyter and spark-submit workloads."""

import logging
import os
import sys
from argparse import Namespace
from typing import Any

from .cli import parse_args
from .config_loader import EnvironmentConfig, load_environment_config

LOGGER = logging.getLogger(__name__)


def _login_spark_writer(spark: Any) -> None:
    """Log an Airflow Spark driver in with its mounted writer keytab.

    Jupyter sessions omit these deployment variables and retain their own
    interactive Kerberos login. Airflow's per-run container supplies both.

    Args:
        spark: Started SparkSession with Hadoop Kerberos configuration.

    Raises:
        RuntimeError: If only one deployment credential setting is provided
            or Hadoop UGI does not acquire Kerberos credentials.
        FileNotFoundError: If the configured keytab is unavailable.
    """
    principal = os.environ.get("SPARK_WRITER_PRINCIPAL")
    keytab = os.environ.get("SPARK_WRITER_KEYTAB")
    if not principal and not keytab:
        return
    if not principal or not keytab:
        raise RuntimeError("SPARK_WRITER_PRINCIPAL and SPARK_WRITER_KEYTAB must be configured together.")
    if not os.path.isfile(keytab):
        raise FileNotFoundError("Configured Spark writer keytab is unavailable.")

    ugi = spark.sparkContext._jvm.org.apache.hadoop.security.UserGroupInformation
    ugi.loginUserFromKeytab(principal, keytab)
    login_user = ugi.getLoginUser()
    if not login_user.hasKerberosCredentials() or not login_user.isFromKeytab():
        raise RuntimeError("Spark Hadoop UGI did not acquire Kerberos credentials from keytab.")
    LOGGER.info("Spark Hadoop UGI logged in from keytab as %s", login_user.getUserName())


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
        _login_spark_writer(spark)
        config_dir = args.config_dir
        if config_dir == "spark-files":
            from pyspark import SparkFiles

            config_dir = SparkFiles.getRootDirectory()

        config = load_environment_config(args.environment, config_dir)
    except Exception:
        spark.stop()
        raise

    return spark, config
