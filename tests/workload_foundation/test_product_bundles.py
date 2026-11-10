"""Per-product configs: configs/<product>/<env>.yml before configs/<env>.yml.

Bundle names, DAG ID prefixes, and environments are the platform's job (lakehouse_dags).
"""

import pytest

from config_loader import load_environment_config


def write(path, database):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"storage_path: s3a://bucket/{database}/\ndatabase_name: {database}\n", encoding="utf-8")


def test_product_config_overrides_the_shared_one_and_falls_back(tmp_path):
    write(tmp_path / "prod.yml", "shared_db")
    write(tmp_path / "sales" / "prod.yml", "sales_db")
    assert load_environment_config("prod", tmp_path, "sales")["database_name"] == "sales_db"
    assert load_environment_config("prod", tmp_path, "default")["database_name"] == "shared_db"
    assert load_environment_config("prod", tmp_path)["database_name"] == "shared_db"


@pytest.mark.parametrize("product", ["../prod", "Sales", "x", "", "a" * 21])
def test_invalid_product_names_are_refused(tmp_path, product):
    write(tmp_path / "prod.yml", "shared_db")
    with pytest.raises(ValueError, match="data product"):
        load_environment_config("prod", tmp_path, product)
