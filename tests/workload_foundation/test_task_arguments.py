"""Declared task arguments: the command line in Airflow, widgets or TASK_ARGS in Jupyter (P3 to P6)."""

import os
import sys
import types

import pytest
from hypothesis import given, seed, settings, strategies as st

from notebooks.common import cli

HYPOTHESIS_SEED = int(os.environ.get("HYPOTHESIS_SEED", "0"))
DECLARATION = {"entity": {"required": True}, "scale_factor": {"default": "0.01"}, "note": {}}


@pytest.fixture
def notebook(monkeypatch):
    """A Jupyter kernel with a notebook namespace the parser reads."""
    namespace = {}
    monkeypatch.setitem(sys.modules, "ipykernel", types.ModuleType("ipykernel"))
    monkeypatch.setattr(cli, "_notebook_namespace", lambda: namespace)
    monkeypatch.setattr(sys, "argv", ["kernel", "--", "--entity", "from-the-kernel-argv"])
    return namespace


def widget(text):
    return types.SimpleNamespace(value=text)


def test_command_line_values_are_strings_and_defaults_fill_the_rest():
    parsed = cli.parse_task_args(DECLARATION, ["--entity", "orders"])
    assert dict(parsed) == {"entity": "orders", "scale_factor": "0.01", "note": None}
    parsed = cli.parse_task_args(DECLARATION, ["--scale-factor=1e9", "--entity", "not-checked", "--note=--x"])
    assert dict(parsed) == {"entity": "not-checked", "scale_factor": "1e9", "note": "--x"}  # values are never checked
    with pytest.raises(TypeError):
        parsed["entity"] = "x"


def test_structural_problems_are_reported_together_and_exit_2(capsys):
    with pytest.raises(SystemExit) as error:
        cli.parse_task_args(DECLARATION, ["--entityy", "x", "stray", "--note", "a", "--note", "b", "--scale-factor"], prog="job.py")
    assert error.value.code == 2
    assert capsys.readouterr().err.splitlines() == [
        "unknown option --entityy",
        "unexpected argument 'stray'",
        "option --note is given twice",
        "option --scale-factor needs a value",
        "option --entity is required",
        "usage: job.py --entity ENTITY [--scale-factor SCALE_FACTOR] [--note NOTE]",
    ]


@pytest.mark.parametrize(
    "declaration",
    [
        {"Entity": {}},
        {"a-b": {}},
        {"x": {"type": "int"}},
        {"x": {"required": "yes"}},
        {"x": {"default": 3}},
        {"x": {"required": True, "default": "a"}},
        ["entity"],
    ],
)
def test_invalid_declarations_are_refused_before_parsing(declaration):
    with pytest.raises(cli.TaskArgumentError, match="Invalid task argument declaration"):
        cli.parse_task_args(declaration, [])


def test_jupyter_reads_widgets_first_then_task_args_and_never_the_kernel_argv(notebook):
    notebook["TASK_ARGS"] = ["--entity", "from-task-args"]
    assert cli.parse_task_args(DECLARATION)["entity"] == "from-task-args"
    notebook["LAKEHOUSE_WIDGETS"] = {"entity": widget("orders"), "scale_factor": widget("")}
    assert dict(cli.parse_task_args(DECLARATION)) == {"entity": "orders", "scale_factor": "0.01", "note": None}
    assert cli.task_args() == ["--entity", "from-task-args"]
    del notebook["TASK_ARGS"]
    assert cli.task_args() == []


def test_jupyter_problems_raise_instead_of_ending_the_kernel(notebook, monkeypatch):
    monkeypatch.setenv("JPY_SESSION_NAME", "/home/jovyan/work/repo/notebooks/workload/generate_tpch.py")
    notebook["LAKEHOUSE_WIDGETS"] = {"entity": widget(""), "colour": widget("red")}
    with pytest.raises(cli.TaskArgumentError) as error:
        cli.parse_task_args(DECLARATION)
    assert str(error.value).splitlines() == [
        "widget 'colour' is not a declared argument",
        "option --entity is required",
        "usage: generate_tpch.py --entity ENTITY [--scale-factor SCALE_FACTOR] [--note NOTE]",
    ]
    notebook.clear()
    notebook["TASK_ARGS"] = "--entity orders"
    with pytest.raises(cli.TaskArgumentError, match="TASK_ARGS must be a list of strings"):
        cli.parse_task_args(DECLARATION)


# --- Properties ----------------------------------------------------------------------

names = st.from_regex(r"[a-z][a-z0-9_]{0,12}", fullmatch=True)
values = st.text(st.characters(categories=("L", "N", "P", "S", "Zs")), min_size=1, max_size=20)
specs = st.sampled_from([{}, {"required": True}, {"default": "d"}])


@st.composite
def declared_values(draw):
    declaration = draw(st.dictionaries(names, specs, min_size=1, max_size=6))
    options = {cli.option_name(n) for n in declaration}
    if len(options) != len(declaration):  # names equal after _ -> - are one option
        declaration = {n: s for n, s in declaration.items() if "_" not in n} or {"entity": {}}
    given_values = {n: draw(values) for n in declaration if declaration[n].get("required") or draw(st.booleans())}
    return declaration, given_values


def render(given_values, order, equals):
    tokens = []
    for name in order:
        if name in given_values:
            value = given_values[name]
            tokens += [f"{cli.option_name(name)}={value}"] if equals or value.startswith("-") else [cli.option_name(name), value]
    return tokens


@seed(HYPOTHESIS_SEED)
@settings(max_examples=150, print_blob=True)
@given(declared_values(), st.data())
def test_p3_rendered_arguments_parse_back_to_the_same_values(case, data):
    declaration, given_values = case
    order = data.draw(st.permutations(list(declaration)))
    parsed = cli.parse_task_args(declaration, render(given_values, order, data.draw(st.booleans())))
    assert dict(parsed) == {n: given_values.get(n, s.get("default")) for n, s in declaration.items()}


@seed(HYPOTHESIS_SEED)
@settings(max_examples=100, print_blob=True)
@given(declared_values())
def test_p4_widgets_task_args_and_the_command_line_agree(case):
    declaration, given_values = case
    from_line = cli.parse_task_args(declaration, render(given_values, list(declaration), True))
    namespace = {"LAKEHOUSE_WIDGETS": {n: widget(given_values.get(n, "")) for n in declaration}}
    original = cli._notebook_namespace
    sys.modules.setdefault("ipykernel", types.ModuleType("ipykernel"))
    try:
        cli._notebook_namespace = lambda: namespace
        from_widgets = cli.parse_task_args(declaration)
        namespace.clear()
        namespace["TASK_ARGS"] = render(given_values, list(declaration), False)
        from_task_args = cli.parse_task_args(declaration)
    finally:
        cli._notebook_namespace = original
        sys.modules.pop("ipykernel", None)
    assert dict(from_line) == dict(from_widgets) == dict(from_task_args)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=100, print_blob=True)
@given(declared_values(), st.sampled_from(["unknown", "repeat", "drop_required"]), st.data())
def test_p5_a_broken_argument_list_never_yields_a_result(case, breakage, data):
    declaration, given_values = case
    tokens = render(given_values, list(declaration), True)
    if breakage == "unknown":
        tokens.append("--zz-not-declared=1")
    elif breakage == "repeat" and tokens:
        tokens.append(tokens[0])
    else:
        required = [n for n, s in declaration.items() if s.get("required")]
        if not required:
            return
        tokens = [t for t in tokens if not t.startswith(cli.option_name(required[0]) + "=")]
    if breakage == "repeat" and not tokens:
        return
    with pytest.raises(SystemExit):
        cli.parse_task_args(declaration, tokens)


@seed(HYPOTHESIS_SEED)
@settings(max_examples=200, print_blob=True)
@given(names, names)
def test_p6_option_names_are_one_to_one_except_for_underscore_and_hyphen(first, second):
    assert cli.option_name(first).startswith("--") and cli.option_name(cli.option_name(first)[2:].replace("-", "_")) == cli.option_name(first)
    assert (cli.option_name(first) == cli.option_name(second)) == (first.replace("_", "-") == second.replace("_", "-"))
