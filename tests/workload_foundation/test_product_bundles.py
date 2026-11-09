"""Data product bundles: DAG ID prefixes, environments, and per-product configs."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from config_loader import load_environment_config
from dag_defaults import identity_for_bundle, product_for_bundle

PRODUCTS = st.from_regex(r"[a-z][a-z0-9]{1,19}", fullmatch=True).filter(lambda name: name != "lakehouse")


def bundle_dags(tmp_path, bundle_name, versioned=False):
    middle = ("versions", "abc123") if versioned else ("tracking_repo",)
    dags_dir = tmp_path.joinpath("dag_bundles", bundle_name, *middle, "dags")
    dags_dir.mkdir(parents=True, exist_ok=True)
    return dags_dir


@pytest.mark.parametrize(
    ("bundle_name", "identity", "product"),
    [
        ("default-main", ("default-main", "prod"), "default"),
        ("default-uat", ("default-uat", "uat"), "default"),
        ("sales-main", ("sales-main", "prod"), "sales"),
        ("lakehouse-main", ("main", "prod"), None),
        ("lakehouse-uat", ("uat", "uat"), None),
        ("default-dev", ("dev", "dev"), None),
        ("Sales-main", ("dev", "dev"), None),
    ],
)
def test_product_bundles_prefix_dag_ids_with_the_bundle_name(tmp_path, bundle_name, identity, product):
    for versioned in (False, True):
        dags_dir = bundle_dags(tmp_path, bundle_name, versioned)
        assert identity_for_bundle(dags_dir) == identity
        assert product_for_bundle(dags_dir) == product


@settings(print_blob=True)
@given(product=PRODUCTS, branch=st.sampled_from(["main", "uat"]))
def test_every_product_bundle_gives_its_own_prefix(tmp_path_factory, product, branch):
    dags_dir = bundle_dags(tmp_path_factory.mktemp("bundle"), f"{product}-{branch}")
    prefix, environment = identity_for_bundle(dags_dir)
    assert prefix == f"{product}-{branch}" and environment == {"main": "prod", "uat": "uat"}[branch]
    assert product_for_bundle(dags_dir) == product


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
