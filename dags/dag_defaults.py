"""Shared default settings for repository Airflow DAGs."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SUPPORTED_ENVIRONMENTS = ("dev", "uat", "prod")
MAIN_BUNDLE_NAME = "lakehouse-main"
PROD_BUNDLE_NAME = "lakehouse-prod"
UAT_BUNDLE_NAME = "lakehouse-uat"
# Data product bundles from the lakehouse platform: <product>-main and <product>-uat.
PRODUCT_BUNDLE_PATTERN = re.compile(r"^(?P<product>[a-z][a-z0-9]{1,19})-(?P<branch>main|uat)$")
LEGACY_PRODUCT_NAMES = ("lakehouse",)


def bundle_name_for(dags_dir: Path) -> str | None:
    """Return the Airflow bundle name from the checkout path, if it has one.

    Args:
        dags_dir: ``dags/`` directory inside the current bundle checkout.

    Returns:
        The bundle name, or ``None`` for non-versioned local DAG paths.
    """
    resolved_dags_dir = dags_dir.resolve()
    tracking_repo_dir = next(
        (parent for parent in resolved_dags_dir.parents if parent.name == "tracking_repo"),
        None,
    )
    if tracking_repo_dir is not None:
        bundle_name = tracking_repo_dir.parent.name
    else:
        versions_dir = next(
            (parent for parent in resolved_dags_dir.parents if parent.name == "versions"),
            None,
        )
        if versions_dir is None:
            return None
        bundle_name = versions_dir.parent.name
    return bundle_name


def product_for_bundle(dags_dir: Path) -> str | None:
    """Return the data product whose bundle holds these DAGs.

    Args:
        dags_dir: ``dags/`` directory inside the current bundle checkout.

    Returns:
        The product name for ``<product>-main``/``<product>-uat`` bundles, or
        ``None`` for legacy ``lakehouse-*`` bundles and local paths.
    """
    match = PRODUCT_BUNDLE_PATTERN.fullmatch(bundle_name_for(dags_dir) or "")
    if match is None or match.group("product") in LEGACY_PRODUCT_NAMES:
        return None
    return match.group("product")


def identity_for_bundle(dags_dir: Path) -> tuple[str, str]:
    """Select the DAG ID prefix and workload environment for a bundle.

    Args:
        dags_dir: ``dags/`` directory inside the current bundle checkout.

    Returns:
        A ``(dag_id_prefix, workload_environment)`` pair: ``("<product>-main",
        "prod")`` and ``("<product>-uat", "uat")`` for data product bundles, so
        DAG IDs start with the bundle name the token broker checks;
        ``("main", "prod")`` and ``("uat", "uat")`` for the legacy
        ``lakehouse-*`` bundles; and ``("dev", "dev")`` for other bundle names
        or non-versioned local DAG paths.
    """
    bundle_name = bundle_name_for(dags_dir)
    if bundle_name in (MAIN_BUNDLE_NAME, PROD_BUNDLE_NAME):
        return "main", "prod"
    if bundle_name == UAT_BUNDLE_NAME:
        return "uat", "uat"
    if product_for_bundle(dags_dir) is not None:
        return bundle_name, "prod" if bundle_name.endswith("-main") else "uat"
    return "dev", "dev"


def standard_dag_kwargs(
    environment: str,
    workload_name: str,
    description: str,
    schedule: str | None,
    tags: Iterable[str] = (),
    dag_id_prefix: str | None = None,
) -> dict[str, Any]:
    """Build the common settings used by manual lakehouse DAGs.

    Args:
        environment: Environment identity declared by this Git branch.
        workload_name: Short name used in the DAG ID and tags.
        description: Human-readable description for the DAG.
        schedule: Airflow schedule; ``None`` creates a manual-only DAG.
        tags: Additional workload-specific tags.
        dag_id_prefix: Optional DAG ID/tag prefix when it differs from the
            workload environment, such as ``main`` for the ``prod`` config.

    Returns:
        Keyword arguments for constructing an Airflow DAG with standard
        schedule, start-date, catchup, tagging, and bundle-version settings.
    """
    prefix = dag_id_prefix or environment
    return {
        "dag_id": f"{prefix}-{workload_name}",
        "description": description,
        "start_date": datetime(2024, 1, 1),
        "schedule": schedule,
        "catchup": False,
        "tags": [prefix, *tags],
        "rerun_with_latest_version": False,
    }
