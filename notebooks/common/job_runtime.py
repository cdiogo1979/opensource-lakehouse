"""Shared startup helpers for Jupyter and spark-submit workloads."""

import os
import sys
from argparse import Namespace
from typing import Any

from .cli import parse_args
from .config_loader import EnvironmentConfig, load_environment_config

CATALOGS = {"lakehouse": "lakehouse", "lakehouse_uat": "lakehouse_uat", "lakehouse_dev": "lakehouse_dev"}
AUTH_MANAGER = "local.lakehouse.spark.auth.LakehouseTokenAuthManager"


def _select_token_provider() -> None:
    """Select one broker adapter and seed its initial JWT in process memory."""
    provider = os.environ.get("LAKEHOUSE_TOKEN_PROVIDER")
    if provider == "airflow":
        required = (
            "LAKEHOUSE_INITIAL_ACCESS_TOKEN",
            "LAKEHOUSE_TOKEN_BROKER_URL",
            "LAKEHOUSE_TOKEN_BROKER_CA",
            "LAKEHOUSE_RUN_HANDLE",
            "LAKEHOUSE_RUN_CAPABILITY",
        )
        if any(not os.environ.get(key) for key in required):
            raise RuntimeError("Airflow Spark token renewal is missing required run-scoped configuration.")
        return
    if provider not in (None, "jupyter"):
        raise RuntimeError("Unsupported Lakehouse token provider.")

    if "ipykernel" in sys.modules or provider == "jupyter":
        if not os.environ.get("JUPYTERHUB_API_TOKEN"):
            raise RuntimeError("The authenticated JupyterHub server token is unavailable.")
        from lakehouse_broker_client import request_user_token

        broker_token = request_user_token()
        os.environ["LAKEHOUSE_TOKEN_PROVIDER"] = "jupyter"
        os.environ["LAKEHOUSE_INITIAL_ACCESS_TOKEN"] = broker_token.access_token
        os.environ.setdefault("LAKEHOUSE_TOKEN_BROKER_URL", "https://jupyterhub:8443/api/v1/token")
        os.environ.setdefault("LAKEHOUSE_TOKEN_BROKER_CA", "/run/certs/jupyterhub-broker-ca.crt")
        return
    raise RuntimeError("Set an authenticated JupyterHub or Airflow token provider before starting Spark.")


def _configure_rest_catalogs(builder: Any, default_catalog: str) -> Any:
    if default_catalog not in CATALOGS:
        raise RuntimeError("The environment selected an unsupported Polaris catalog.")
    builder = builder.config("spark.sql.defaultCatalog", default_catalog)
    for catalog, warehouse in CATALOGS.items():
        prefix = f"spark.sql.catalog.{catalog}"
        settings = {
            "": "org.apache.iceberg.spark.SparkCatalog",
            ".type": "rest",
            ".uri": "http://polaris:8181/api/catalog",
            ".warehouse": warehouse,
            ".rest.auth.type": AUTH_MANAGER,
            ".io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
            ".header.Polaris-Realm": "lakehouse",
            ".header.X-Iceberg-Access-Delegation": "vended-credentials",
        }
        for suffix, value in settings.items():
            builder = builder.config(prefix + suffix, value)
    return builder


def start_spark_job(app_name: str, argv: Any = None) -> tuple[Any, EnvironmentConfig]:
    """Load environment settings and start a broker-authenticated Spark session."""
    if "ipykernel" in sys.modules:
        args = Namespace(
            environment=os.environ.get("LAKEHOUSE_ENVIRONMENT", "dev"),
            config_dir=os.environ.get("LAKEHOUSE_CONFIG_DIR"),
        )
    else:
        args = parse_args(argv)

    config_dir = args.config_dir
    if config_dir == "spark-files":
        # spark-submit does not initialize SparkFiles until SparkContext exists,
        # but the catalog selection is needed before SparkSession startup.
        # Airflow already mounts the selected Bundle, so use its config folder.
        config_dir = os.environ.get("LAKEHOUSE_BUNDLE_CONFIG_DIR", "/opt/lakehouse-bundle/configs")
    config = load_environment_config(args.environment, config_dir)
    _select_token_provider()

    from pyspark.sql import SparkSession

    spark = (
        _configure_rest_catalogs(SparkSession.builder.appName(f"{args.environment}-{app_name}"), config["catalog_name"])
        .config("spark.redaction.regex", r"(?i)secret|password|token|access[.]?key|credential")
        .config("spark.sql.redaction.options.regex", r"(?i)secret|password|token|access[.]?key|credential")
        .getOrCreate()
    )
    return spark, config
