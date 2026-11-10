"""The Jupyter %run scripts in notebooks/common: inert on import, and their rules (BR-R, BR-W)."""

import types
from pathlib import Path

import pytest

from notebooks.common import cli, jupyter_environment_resolver as resolver, jupyter_input_widget_helper as widgets

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_the_resolver_finds_the_clone_that_holds_the_notebook(tmp_path):
    assert resolver.find_repository_root(REPOSITORY_ROOT / "notebooks" / "workload" / "sample") == REPOSITORY_ROOT
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
    for path in (REPOSITORY_ROOT / "notebooks/workload").glob("*/*.py"):
        text = path.read_text()
        assert "jupyter_helper" not in text
        assert "# %run ./" not in text
    assert not (REPOSITORY_ROOT / "notebooks/workload/jupyter_helper.py").exists()


INITIALIZATION = ["# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp", "# %run ../../common/jupyter_environment_resolver.py"]


def test_every_notebook_starts_with_the_initialization_section():
    """CR-4: the first code cells of each notebook install the extras and run the resolver."""
    for path in sorted((REPOSITORY_ROOT / "notebooks/workload").glob("*/*.py")):
        cells = [cell.strip() for cell in path.read_text().split("# %%")[1:]]
        code = [cell for cell in cells if not cell.startswith("[markdown]")]
        assert code[:2] == INITIALIZATION, path.name
        assert cells[1].startswith("[markdown]\n# ## Initialization"), path.name


def sections(text):
    """(heading, code cells) for each "## " markdown section of a py:percent notebook."""
    result = []
    for cell in text.split("# %%")[1:]:
        cell = cell.strip()
        if cell.startswith("[markdown]"):
            heading = next((line[5:] for line in cell.splitlines() if line.startswith("# ## ")), None)
            if heading:
                result.append((heading, []))
        elif result:
            result[-1][1].append(cell)
    return result


def test_every_notebook_has_initialization_imports_its_own_sections_and_execution():
    """CR-5: the same frame in every notebook; the job's own sections sit between Imports and Execution."""
    for path in sorted((REPOSITORY_ROOT / "notebooks/workload").glob("*/*.py")):
        found = sections(path.read_text())
        headings = [heading for heading, _ in found]
        assert headings[:2] == ["Initialization", "Imports"] and headings[-1] == "Execution", (path.name, headings)
        assert len(headings) > 3, f"{path.name}: no section of its own between Imports and Execution"
        assert found[1][1][0].startswith(("import ", "from ")), path.name
        execution = "\n".join(found[-1][1])
        assert execution.startswith('if __name__ == "__main__":') and path.read_text().count('if __name__ == "__main__":') == 1, path.name


def test_workflows_and_notebooks_live_in_matching_subproject_folders():
    """Every subproject has the same name under workflows/ and notebooks/workload/; nothing is left at the top level."""
    workflows = REPOSITORY_ROOT / "workflows"
    workload = REPOSITORY_ROOT / "notebooks" / "workload"
    assert not list(workflows.glob("*.json")) and not list(workload.glob("*.py"))
    projects = {path.name for path in workflows.iterdir() if path.is_dir()}
    assert projects and projects <= {path.name for path in workload.iterdir() if path.is_dir()}
