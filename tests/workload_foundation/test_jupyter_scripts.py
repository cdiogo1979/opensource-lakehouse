"""The Jupyter %run scripts in notebooks/common: inert on import, and their rules (BR-R, BR-W)."""

import types
from pathlib import Path

import pytest

from notebooks.common import cli, jupyter_environment_resolver as resolver, jupyter_input_widget_helper as widgets

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_the_resolver_finds_the_clone_that_holds_the_notebook(tmp_path):
    assert resolver.find_repository_root(REPOSITORY_ROOT / "notebooks" / "workload") == REPOSITORY_ROOT
    with pytest.raises(FileNotFoundError, match="inside a clone"):
        resolver.find_repository_root(tmp_path)


def test_the_spark_application_takes_the_notebook_name():
    assert resolver.notebook_name({"JPY_SESSION_NAME": "/home/jovyan/work/repo/notebooks/workload/generate_tpch.py"}) == "generate_tpch"
    assert resolver.notebook_name({"JPY_SESSION_NAME": "/x/Untitled1.ipynb"}) == "Untitled1"
    assert resolver.notebook_name({}) == "notebook"


def test_importing_the_scripts_starts_nothing():
    assert not hasattr(resolver, "spark") and not hasattr(widgets, "LAKEHOUSE_WIDGETS")


@pytest.mark.parametrize("value", [None, [], "entity", ["Entity"], ["entity", "entity"], ["scale-factor"], [3]])
def test_widget_list_must_be_distinct_argument_names(value):
    with pytest.raises(ValueError):
        widgets.check_widget_list(value)


def test_widgets_keep_their_text_and_follow_the_list():
    existing = {"entity": types.SimpleNamespace(value="orders"), "old": types.SimpleNamespace(value="x")}
    built = widgets.build_widgets(["scale_factor", "entity"], existing, lambda name: types.SimpleNamespace(value=""))
    assert list(built) == ["scale_factor", "entity"] and built["entity"] is existing["entity"] and "old" not in built


def test_the_helper_and_the_parser_share_the_variable_and_name_rule():
    assert widgets.WIDGETS_VARIABLE == cli.WIDGETS_VARIABLE
    assert widgets.WIDGET_NAME.pattern == cli.ARGUMENT_NAME.pattern


def test_entry_points_run_the_scripts_from_common():
    for path in (REPOSITORY_ROOT / "notebooks/workload").glob("*.py"):
        text = path.read_text()
        assert "jupyter_helper" not in text
        assert "# %run ./" not in text
    assert not (REPOSITORY_ROOT / "notebooks/workload/jupyter_helper.py").exists()


INITIALIZATION = ["# !lakehouse-install-requirements ~/work/opensource-lakehouse", "# %run ../common/jupyter_environment_resolver.py"]


def test_every_notebook_starts_with_the_initialization_section():
    """CR-4: the first code cells of each notebook install the extras and run the resolver."""
    for path in sorted((REPOSITORY_ROOT / "notebooks/workload").glob("*.py")):
        cells = [cell.strip() for cell in path.read_text().split("# %%")[1:]]
        code = [cell for cell in cells if not cell.startswith("[markdown]")]
        assert code[:2] == INITIALIZATION, path.name
        assert cells[1].startswith("[markdown]\n# ## Initialization"), path.name
