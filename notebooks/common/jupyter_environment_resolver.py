"""Jupyter start-up: this clone's configuration and the platform's Spark session.

Run it from a notebook in ``notebooks/workload/``::

    # %env LAKEHOUSE_ENVIRONMENT=uat          (optional; dev when unset)
    # %run ../common/jupyter_environment_resolver.py

It finds the repository clone that holds the notebook, puts it on the import
path, and defines ``spark``, ``config`` and ``repository_root`` in the notebook.
The Spark application is ``<env>-<notebook name>``. Imported as a module (as
Airflow runs and tests do), it only defines functions.
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

MARKER = Path("notebooks") / "common" / "job_runtime.py"


def find_repository_root(start: Path) -> Path:
    """The nearest folder at or above ``start`` holding ``notebooks/common/job_runtime.py`` and ``configs/``.

    Raises:
        FileNotFoundError: The notebook is not inside a clone of the repository.
    """
    start = Path(start).resolve()
    for candidate in (start, *start.parents):
        if (candidate / MARKER).is_file() and (candidate / "configs").is_dir():
            return candidate
    raise FileNotFoundError("Open the notebook inside a clone of the data product repository.")


def notebook_name(environ: Optional[Any] = None) -> str:
    """The notebook's file name without extension, from Jupyter's ``JPY_SESSION_NAME``; ``notebook`` when unknown."""
    session = (os.environ if environ is None else environ).get("JPY_SESSION_NAME")
    return Path(session).stem if session else "notebook"


def resolve(start: Optional[Path] = None) -> tuple:
    """Start the notebook's Spark session with this clone's config; returns ``(spark, config, repository_root)``."""
    root = find_repository_root(Path.cwd() if start is None else start)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from notebooks.common.job_runtime import jupyter_environment, start_spark_job

    environment = jupyter_environment()
    spark, config = start_spark_job(notebook_name())
    print(f"Lakehouse environment {environment}: {root / 'configs' / (environment + '.yml')}")
    return spark, config, root


if __name__ == "__main__" and "ipykernel" in sys.modules:
    spark, config, repository_root = resolve()
