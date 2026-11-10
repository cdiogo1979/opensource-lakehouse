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
    for path in notebooks():
        text = path.read_text()
        assert "jupyter_helper" not in text
        assert "# %run ./" not in text
    assert not (REPOSITORY_ROOT / "notebooks/workload/jupyter_helper.py").exists()


LAYERS = ("bronze", "silver", "gold", "ops", "deploy")


def notebooks():
    """Every notebook in notebooks/workload/<project>/ and its layer folders."""
    workload = REPOSITORY_ROOT / "notebooks/workload"
    return sorted([*workload.glob("*/*.py"), *workload.glob("*/*/*.py")])


def initialization(path):
    """The Initialization lines for a notebook, with the %run path matching its depth."""
    up = "../" * (len(path.relative_to(REPOSITORY_ROOT / "notebooks").parts) - 1)
    return ["# !lakehouse-install-requirements ~/work/opensource-lakehouse-sample-dp", f"# %run {up}common/jupyter_environment_resolver.py"]


def test_every_notebook_starts_with_the_initialization_section():
    """CR-4: the first code cells of each notebook install the extras and run the resolver."""
    for path in sorted(notebooks()):
        cells = [cell.strip() for cell in path.read_text().split("# %%")[1:]]
        code = [cell for cell in cells if not cell.startswith("[markdown]")]
        assert code[:2] == initialization(path), path.name
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
    for path in sorted(notebooks()):
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


def test_layer_folders_are_only_the_five_medallion_folders_one_level_deep():
    for project in (REPOSITORY_ROOT / "notebooks/workload").iterdir():
        if project.is_dir() and project.name != "__pycache__":
            for folder in project.iterdir():
                if folder.is_dir() and folder.name != "__pycache__":
                    assert folder.name in LAYERS, f"{folder}: not a layer folder ({', '.join(LAYERS)})"
                    assert not [p for p in folder.iterdir() if p.is_dir() and p.name != "__pycache__"], f"{folder}: no deeper folders"


def test_the_initialization_path_follows_the_notebook_depth():
    root = REPOSITORY_ROOT / "notebooks/workload"
    assert initialization(root / "sample/generate_tpch.py")[1] == "# %run ../../common/jupyter_environment_resolver.py"
    assert initialization(root / "sample/bronze/load.py")[1] == "# %run ../../../common/jupyter_environment_resolver.py"
