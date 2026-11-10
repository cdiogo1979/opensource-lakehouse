# %% [markdown]
# # Generate TPC-H data and count one entity
#
# This Jupytext `py:percent` notebook generates the TPC-H dataset in memory with
# DuckDB (the `duckdb` package from this repository's `requirements.txt`), counts
# the rows of one TPC-H entity, and checks the count against the TPC-H rules. It
# starts no Spark session and writes nothing.
#
# In Airflow, `workflows/generate_tpch.json` runs it once per entity with
# `--entity <name>` after `--`; `--scale-factor` is optional (default 0.01).
# In Jupyter, run `lakehouse-install-requirements` once, restart the kernel, and
# set `ENTITY` and `SCALE_FACTOR` below. DuckDB downloads its `tpch` extension
# the first time it is used, so the first run needs network access.

# %%
import argparse
import logging
import sys
from decimal import Decimal, InvalidOperation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# %% [markdown]
# ## Settings for Jupyter
#
# Airflow passes these as task arguments instead.

# %%
ENTITY = "lineitem"
SCALE_FACTOR = "0.01"

# %% [markdown]
# ## TPC-H rules
#
# `region` and `nation` have fixed sizes. The other entities, except `lineitem`,
# have exactly their base count times the scale factor. Each order has 1 to 7
# lines, so `lineitem` is checked against the `orders` count. Scale factors are
# kept small (0.001 to 1, at most three decimal places) so every count is whole.

# %%
ENTITIES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")
FIXED_COUNTS = {"region": 5, "nation": 25}
BASE_COUNTS = {"supplier": 10_000, "customer": 150_000, "part": 200_000, "partsupp": 800_000, "orders": 1_500_000}
LINES_PER_ORDER = (1, 7)
SCALE_STEP = Decimal("0.001")
MIN_SCALE_FACTOR = Decimal("0.001")
MAX_SCALE_FACTOR = Decimal("1")


def parse_scale_factor(text: str) -> Decimal:
    """A TPC-H scale factor from 0.001 to 1 with at most three decimal places.

    Args:
        text: The scale factor as written, for example ``"0.01"``.

    Returns:
        The exact decimal value.

    Raises:
        ValueError: The text is not such a number.
    """
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        value = None
    if value is None or not value.is_finite() or not MIN_SCALE_FACTOR <= value <= MAX_SCALE_FACTOR or value != value.quantize(SCALE_STEP):
        raise ValueError(f"the scale factor must be a number from 0.001 to 1 with at most three decimal places, not {text!r}")
    return value


def expected_count(entity: str, scale_factor: Decimal, orders_count: int = 0) -> tuple:
    """The inclusive (lowest, highest) row count TPC-H allows for an entity.

    Args:
        entity: One of ``ENTITIES``.
        scale_factor: A value accepted by ``parse_scale_factor``.
        orders_count: The generated ``orders`` count, needed for ``lineitem``.

    Returns:
        ``(lowest, highest)``; equal except for ``lineitem``.
    """
    if entity in FIXED_COUNTS:
        return FIXED_COUNTS[entity], FIXED_COUNTS[entity]
    if entity in BASE_COUNTS:
        count = int(BASE_COUNTS[entity] * scale_factor)
        return count, count
    if entity == "lineitem":
        return LINES_PER_ORDER[0] * orders_count, LINES_PER_ORDER[1] * orders_count
    raise ValueError(f"unknown TPC-H entity {entity!r}; expected one of {', '.join(ENTITIES)}")


def check_count(entity: str, scale_factor: Decimal, count: int, orders_count: int = 0) -> None:
    """Raise when a generated count breaks the TPC-H rule for its entity.

    Raises:
        RuntimeError: The count is outside ``expected_count``.
    """
    lowest, highest = expected_count(entity, scale_factor, orders_count)
    if not lowest <= count <= highest:
        expected = str(lowest) if lowest == highest else f"{lowest} to {highest}"
        raise RuntimeError(f"TPC-H {entity} at scale factor {scale_factor}: {count} rows, expected {expected}")


def parse_task_args(args: list) -> tuple:
    """The entity and scale factor from the workflow task's arguments (after ``--``).

    Exits with status 2 and a usage message for invalid arguments.
    """
    parser = argparse.ArgumentParser(prog="generate_tpch.py", description="Generate TPC-H data and count one entity.")
    parser.add_argument("--entity", required=True, choices=ENTITIES)
    parser.add_argument("--scale-factor", default="0.01")
    parsed = parser.parse_args(args)
    try:
        scale_factor = parse_scale_factor(parsed.scale_factor)
    except ValueError as error:
        parser.error(str(error))
    return parsed.entity, scale_factor


# %% [markdown]
# ## Generate and count
#
# The entity name is checked against `ENTITIES` before it reaches SQL.


# %%
def generate_tpch(entity: str, scale_factor: Decimal) -> int:
    """Generate TPC-H at ``scale_factor`` in memory, count ``entity``, and check the count.

    Returns:
        The entity's row count.
    """
    if entity not in ENTITIES:
        raise ValueError(f"unknown TPC-H entity {entity!r}; expected one of {', '.join(ENTITIES)}")
    import duckdb

    with duckdb.connect() as connection:
        connection.execute(f"CALL dbgen(sf={parse_scale_factor(str(scale_factor))})")
        count = connection.execute(f"SELECT count(*) FROM {entity}").fetchone()[0]  # nosec B608 - entity is one of ENTITIES
        orders_count = connection.execute("SELECT count(*) FROM orders").fetchone()[0] if entity == "lineitem" else 0
    logger.info("TPC-H %s at scale factor %s: %d rows", entity, scale_factor, count)
    check_count(entity, scale_factor, count, orders_count)
    return count


# %%
if __name__ == "__main__":
    # Importing this workload from pytest must not parse the caller's arguments.
    if "ipykernel" in sys.modules:
        entity, scale_factor = ENTITY, parse_scale_factor(SCALE_FACTOR)
    else:
        from notebooks.common.cli import task_args

        entity, scale_factor = parse_task_args(task_args())
    generate_tpch(entity, scale_factor)
