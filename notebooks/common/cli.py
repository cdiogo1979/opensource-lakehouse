"""Shared argument parsing for Spark jobs, in Airflow (command line) and Jupyter (widgets or TASK_ARGS)."""

import argparse
import os
import re
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional

from .config_loader import SUPPORTED_ENVIRONMENTS

# Airflow passes a task's workflow "args" after this separator:
#   spark-submit job.py --environment uat --config-dir ... -- --date 2026-11-10
TASK_ARGS_SEPARATOR = "--"
# In Jupyter, a notebook's arguments come from the widgets that jupyter_input_widget_helper.py
# keeps in this notebook variable, else from the notebook's TASK_ARGS list.
WIDGETS_VARIABLE = "LAKEHOUSE_WIDGETS"
TASK_ARGS_VARIABLE = "TASK_ARGS"
ARGUMENT_NAME = re.compile(r"[a-z][a-z0-9_]{0,49}")
SPEC_KEYS = frozenset({"required", "default"})


class TaskArgumentError(ValueError):
    """Every problem with a job's task arguments, followed by its usage line."""


def _split(argv: Optional[list]) -> tuple:
    """Split an argument list at the first ``--`` into (standard, task) arguments."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if TASK_ARGS_SEPARATOR in arguments:
        index = arguments.index(TASK_ARGS_SEPARATOR)
        return arguments[:index], arguments[index + 1 :]
    return arguments, []


def parse_args(argv: Any = None) -> argparse.Namespace:
    """Parse the standard environment and config-directory arguments.

    Args:
        argv: Optional argument list, primarily for direct invocation.

    Returns:
        Parsed environment and optional config directory, plus ``task_args``:
        the workflow task's arguments after ``--`` (empty when there are none).
    """
    standard, extra = _split(argv)
    parser = argparse.ArgumentParser(description="Run a Spark workload using an explicit environment config.")
    parser.add_argument(
        "--environment",
        required=True,
        choices=sorted(SUPPORTED_ENVIRONMENTS),
        help="Environment config to load; no default is selected.",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Directory containing the selected YAML (default: repository configs/).",
    )
    args = parser.parse_args(standard)
    args.task_args = extra
    return args


def _notebook_namespace() -> Optional[dict]:
    """The Jupyter notebook's variables, also while a %run script executes; None outside a kernel."""
    if "ipykernel" not in sys.modules:
        return None
    try:
        from IPython import get_ipython
    except ImportError:
        return None
    shell = get_ipython()
    return None if shell is None else shell.user_ns


def task_args(argv: Any = None) -> list:
    """The workflow task's arguments: after ``--`` on the command line, or the notebook's ``TASK_ARGS`` in Jupyter.

    Args:
        argv: Optional argument list; defaults to ``sys.argv[1:]`` (or ``TASK_ARGS`` in Jupyter).

    Returns:
        The arguments, unchanged; ``[]`` when there are none.

    Raises:
        TaskArgumentError: ``TASK_ARGS`` is not a list of strings.
    """
    if argv is None and "ipykernel" in sys.modules:
        # Never the kernel's own command line.
        value = (_notebook_namespace() or {}).get(TASK_ARGS_VARIABLE, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise TaskArgumentError(f"{TASK_ARGS_VARIABLE} must be a list of strings.")
        return list(value)
    return _split(argv)[1]


def option_name(name: str) -> str:
    """The option for a declared argument name: ``scale_factor`` -> ``--scale-factor``."""
    return "--" + name.replace("_", "-")


def _declaration_problems(declaration: Any) -> list:
    if not isinstance(declaration, Mapping):
        return ["the declaration must be a mapping of argument names to specs"]
    problems, options = [], set()
    for name, spec in declaration.items():
        if not isinstance(name, str) or not ARGUMENT_NAME.fullmatch(name):
            problems.append(f"invalid argument name {name!r}")
            continue
        if option_name(name) in options:
            problems.append(f"argument {name!r} repeats an option")
        options.add(option_name(name))
        if not isinstance(spec, Mapping) or set(spec) - SPEC_KEYS:
            problems.append(f"argument {name!r}: the spec may hold only 'required' and 'default'")
            continue
        if "required" in spec and not isinstance(spec["required"], bool):
            problems.append(f"argument {name!r}: 'required' must be true or false")
        if "default" in spec and not isinstance(spec["default"], str):
            problems.append(f"argument {name!r}: 'default' must be a string")
        if spec.get("required") and "default" in spec:
            problems.append(f"argument {name!r}: a required argument has no default")
    return problems


def _usage(declaration: Mapping, prog: str) -> str:
    names = sorted(declaration, key=lambda name: not declaration[name].get("required"))
    parts = [f"{option_name(n)} {n.upper()}" if declaration[n].get("required") else f"[{option_name(n)} {n.upper()}]" for n in names]
    return " ".join([f"usage: {prog}", *parts])


def _parse_tokens(tokens: list, declaration: Mapping) -> tuple:
    by_option = {option_name(name): name for name in declaration}
    values, problems, index = {}, [], 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token.startswith("--"):
            problems.append(f"unexpected argument {token!r}")
            continue
        option, has_value, value = token.partition("=")
        if option not in by_option:
            problems.append(f"unknown option {option}")
            if not has_value and index < len(tokens) and not tokens[index].startswith("-"):
                index += 1
            continue
        if not has_value:
            if index >= len(tokens) or tokens[index].startswith("-"):
                problems.append(f"option {option} needs a value")
                continue
            value = tokens[index]
            index += 1
        name = by_option[option]
        if name in values:
            problems.append(f"option {option} is given twice")
            continue
        values[name] = value
    return values, problems


def _widget_values(widgets: Mapping, declaration: Mapping) -> tuple:
    values, problems = {}, []
    for name, widget in widgets.items():
        if name not in declaration:
            problems.append(f"widget {name!r} is not a declared argument")
            continue
        text = getattr(widget, "value", "")
        if isinstance(text, str) and text != "":
            values[name] = text
    return values, problems


def _program_name() -> str:
    session = os.environ.get("JPY_SESSION_NAME") if "ipykernel" in sys.modules else None
    return Path(session or sys.argv[0] or "job").name


def parse_task_args(declaration: Mapping, argv: Any = None, prog: Optional[str] = None) -> Mapping:
    """The job's declared task arguments, as strings; values are never converted or checked.

    Each name in ``declaration`` maps to ``{"required": True}``, ``{"default": "<text>"}``
    or ``{}``; ``scale_factor`` is given as ``--scale-factor value`` or ``--scale-factor=value``.
    The values come from the command line after ``--`` (Airflow), or in Jupyter from
    the notebook's input widgets when there are any, else from its ``TASK_ARGS``.

    Args:
        declaration: The job's argument names and specs.
        argv: Optional task arguments (what follows ``--``) instead of the context's source.
        prog: Optional program name for the usage line.

    Returns:
        A read-only mapping of every declared name to its value, its default, or None.

    Raises:
        TaskArgumentError: The declaration is invalid, or, in Jupyter, the arguments are.
        SystemExit: With status 2 and the problems on stderr, outside Jupyter.
    """
    problems = _declaration_problems(declaration)
    if problems:
        raise TaskArgumentError("Invalid task argument declaration: " + "; ".join(problems))
    namespace = _notebook_namespace() if argv is None else None
    widgets = (namespace or {}).get(WIDGETS_VARIABLE)
    if isinstance(widgets, Mapping) and widgets:
        values, problems = _widget_values(widgets, declaration)
    else:
        try:
            tokens = task_args() if argv is None else list(argv)
        except TaskArgumentError as error:
            tokens, problems = [], [str(error)]
        values, token_problems = _parse_tokens(tokens, declaration)
        problems += token_problems
    problems += [f"option {option_name(name)} is required" for name, spec in declaration.items() if spec.get("required") and name not in values]
    if problems:
        message = "\n".join([*problems, _usage(declaration, prog or _program_name())])
        if "ipykernel" in sys.modules:
            raise TaskArgumentError(message)
        print(message, file=sys.stderr)
        raise SystemExit(2)
    return MappingProxyType({name: values.get(name, spec.get("default")) for name, spec in declaration.items()})
