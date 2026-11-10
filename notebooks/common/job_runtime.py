"""Start a workload: this repository's environment config, then the platform's Spark session.

The lakehouse platform owns the Spark session (catalogs, token source, redaction):
``lakehouse_spark`` is on the Python path of both its images. This repository
owns its configuration: every key of ``configs/<env>.yml`` reaches the job.
"""

import os
import sys
from typing import Any

from .cli import parse_args
from .config_loader import SUPPORTED_ENVIRONMENTS, EnvironmentConfig, load_environment_config

JUPYTER_DEFAULT_ENVIRONMENT = "dev"


def jupyter_environment(environ: Any = None) -> str:
    """The environment a Jupyter notebook works in: ``LAKEHOUSE_ENVIRONMENT``, ``dev`` when unset.

    Args:
        environ: Optional mapping instead of ``os.environ``.

    Returns:
        ``dev``, ``uat`` or ``prod``.

    Raises:
        ValueError: The variable holds another value.
    """
    value = (os.environ if environ is None else environ).get("LAKEHOUSE_ENVIRONMENT") or JUPYTER_DEFAULT_ENVIRONMENT
    if value not in SUPPORTED_ENVIRONMENTS:
        supported = ", ".join(sorted(SUPPORTED_ENVIRONMENTS))
        raise ValueError(f"LAKEHOUSE_ENVIRONMENT is {value!r}; expected one of: {supported}.")
    return value


def start_spark_job(app_name: str, argv: Any = None) -> tuple[Any, EnvironmentConfig]:
    """Load the environment config and start the platform's Spark session.

    In Jupyter, the environment comes from ``jupyter_environment()`` and the
    shared ``configs/<env>.yml`` of this clone is used. Elsewhere (``spark-submit``
    in Airflow), ``--environment`` and ``--config-dir`` are parsed, and the
    product the platform sets in ``LAKEHOUSE_PRODUCT`` selects
    ``configs/<product>/<env>.yml`` when it exists.

    Args:
        app_name: The job's name; the Spark application is ``<env>-<app_name>``.
        argv: Optional argument list instead of ``sys.argv[1:]``.

    Returns:
        ``(spark, config)``.

    Raises:
        ValueError: The config has no ``catalog_name``, or the environment is invalid.
    """
    if "ipykernel" in sys.modules:
        environment, config_dir, product = jupyter_environment(), None, None
    else:
        args = parse_args(argv)
        environment, config_dir, product = args.environment, args.config_dir, os.environ.get("LAKEHOUSE_PRODUCT") or None
    config = load_environment_config(environment, config_dir, product)
    catalog = config.get("catalog_name")
    if not isinstance(catalog, str) or not catalog:
        raise ValueError(f"The {environment} config has no catalog_name; it selects the Polaris catalog.")

    from lakehouse_spark import create_spark_session

    return create_spark_session(f"{environment}-{app_name}", catalog), config
