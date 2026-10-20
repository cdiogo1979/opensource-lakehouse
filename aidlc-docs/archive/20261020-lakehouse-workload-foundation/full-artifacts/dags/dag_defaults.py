"""Shared default settings for repository Airflow DAGs."""

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SUPPORTED_ENVIRONMENTS = ("dev", "uat", "prod")
MAIN_BUNDLE_NAME = "lakehouse-main"
PROD_BUNDLE_NAME = "lakehouse-prod"
UAT_BUNDLE_NAME = "lakehouse-uat"


def identity_for_bundle(dags_dir: Path) -> tuple[str, str]:
    """Select the DAG ID prefix and workload environment for a bundle.

    Args:
        dags_dir: ``dags/`` directory inside the current bundle checkout.

    Returns:
        A ``(dag_id_prefix, workload_environment)`` pair: ``("main", "prod")``
        for the main bundle, ``("uat", "uat")`` for UAT, and ``("dev", "dev")``
        for other bundle names or non-versioned local DAG paths.
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
            return "dev", "dev"
        bundle_name = versions_dir.parent.name

    if bundle_name in (MAIN_BUNDLE_NAME, PROD_BUNDLE_NAME):
        return "main", "prod"
    if bundle_name == UAT_BUNDLE_NAME:
        return "uat", "uat"
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
