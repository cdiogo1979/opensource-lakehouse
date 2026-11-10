"""Jupyter input widgets for a job's task arguments.

Run it from a notebook after listing the arguments::

    WIDGET_LIST = ["entity", "scale_factor"]
    # %run ../../common/jupyter_input_widget_helper.py

It shows one text field per name. ``notebooks.common.cli.parse_task_args`` then
reads their text (an empty field means not given), as Airflow passes the
workflow's ``args``. Running it again keeps what was typed. It also puts its own
clone on the import path, so a job that starts no Spark session can import
``notebooks.common``. Imported as a module, it only defines functions.
"""

import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

# The same notebook variable and name rule as notebooks.common.cli (kept here so this
# script also works before the environment resolver has put the clone on the path).
WIDGETS_VARIABLE = "LAKEHOUSE_WIDGETS"
WIDGET_NAME = re.compile(r"[a-z][a-z0-9_]{0,49}")


def check_widget_list(value: Any) -> list:
    """``WIDGET_LIST`` as a list of distinct argument names.

    Raises:
        ValueError: It is missing, not a list, or holds an invalid or repeated name.
    """
    if not isinstance(value, list) or not value:
        raise ValueError('Define WIDGET_LIST as a list of argument names first, for example WIDGET_LIST = ["entity"].')
    invalid = [name for name in value if not isinstance(name, str) or not WIDGET_NAME.fullmatch(name)]
    if invalid:
        raise ValueError(f"WIDGET_LIST holds invalid names: {invalid!r}; use lowercase letters, digits and underscores.")
    if len(set(value)) != len(value):
        raise ValueError("WIDGET_LIST holds a name twice.")
    return list(value)


def build_widgets(names: list, existing: Mapping, make: Callable[[str], Any]) -> dict:
    """The widgets for ``names``, in order: existing ones keep their text, new ones come from ``make``."""
    return {name: existing[name] if name in existing else make(name) for name in names}


def show_widgets(namespace: dict) -> dict:
    """Create or update the notebook's widgets from its ``WIDGET_LIST`` and display them."""
    names = check_widget_list(namespace.get("WIDGET_LIST"))
    import ipywidgets
    from IPython.display import display

    def make(name: str) -> Any:
        return ipywidgets.Text(description=name, style={"description_width": "initial"})

    widgets = build_widgets(names, namespace.get(WIDGETS_VARIABLE) or {}, make)
    namespace[WIDGETS_VARIABLE] = widgets
    display(ipywidgets.VBox(list(widgets.values())))
    return widgets


if __name__ == "__main__" and "ipykernel" in sys.modules:
    from IPython import get_ipython

    # %run sets __file__: this clone is <clone>/notebooks/common/<this file>.
    _clone = str(Path(__file__).resolve().parents[2])
    if _clone not in sys.path:
        sys.path.insert(0, _clone)
    show_widgets(get_ipython().user_ns)
