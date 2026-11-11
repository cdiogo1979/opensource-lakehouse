"""The tpch materialized views (mv-promotion FR-7): declared for the platform's deploy, named by convention, reading silver only."""

import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIEWS = REPOSITORY_ROOT / "materialized_views" / "tpch"
PLACEHOLDERS = {"${catalog}", "${namespace}", "${mv_database}"}
SILVER_TABLES = {f"tpch_{entity}" for entity in ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")}


def statement(path):
    lines = [line for line in path.read_text().splitlines() if not line.lstrip().startswith("--")]
    return "\n".join(lines).strip().rstrip(";")


def test_the_two_tpch_views_are_declared():
    assert sorted(path.stem for path in VIEWS.glob("*.sql")) == ["mv_tpch_current", "mv_tpch_day_nation_segment"]


@pytest.mark.parametrize("path", sorted(VIEWS.glob("*.sql")), ids=lambda path: path.stem)
def test_each_view_follows_the_platform_and_naming_rules(path):
    sql = statement(path)
    assert re.fullmatch(r"mv_tpch_[a-z0-9]+(_[a-z0-9]+)*", path.stem)
    assert sql.startswith(f"CREATE MATERIALIZED VIEW ${{mv_database}}.{path.stem}\n") and ";" not in sql
    assert set(re.findall(r"\$\{[^}]*\}", sql)) <= PLACEHOLDERS
    assert "REFRESH ASYNC" in sql and "COMMENT '" in sql and "lakehouse-mv" not in sql  # the platform adds its marker
    tables = set(re.findall(r"\$\{catalog\}\.\$\{namespace\}\.([a-z0-9_]+)", sql))
    assert tables and tables <= SILVER_TABLES, f"{path.stem} reads {sorted(tables - SILVER_TABLES)}: views read silver tables only"


def test_current_keeps_order_detail_for_the_latest_load_day_only():
    sql = statement(VIEWS / "mv_tpch_current.sql")
    assert "o.o_orderkey" in sql and "l.l_linenumber" in sql and "GROUP BY" not in sql
    assert "WHERE DATE(o.bronze_ingestion_timestamp) = (SELECT MAX(DATE(bronze_ingestion_timestamp)) FROM ${catalog}.${namespace}.tpch_orders)" in sql


def test_day_nation_segment_has_no_order_level_and_groups_by_its_name():
    sql = statement(VIEWS / "mv_tpch_day_nation_segment.sql")
    assert "GROUP BY o.o_orderdate, r.r_name, n.n_name, c.c_mktsegment" in sql
    assert "o.o_orderkey AS" not in sql and "COUNT(DISTINCT o.o_orderkey) AS orders" in sql
