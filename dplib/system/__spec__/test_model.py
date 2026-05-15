import json
from pathlib import Path

import pytest
import yaml

from dplib import settings
from dplib.error import Error
from dplib.models import Catalog, Package, Resource


def test_model_repr():
    resource = Resource.from_path("data/resource.json")
    repr = str(resource)
    assert repr.count(f"'$schema': '{settings.PROFILE_CURRENT_RESOURCE}'")
    assert repr.count("'name': 'name'")
    assert repr.count("'path': 'table.csv'")


def test_model_custom_properties():
    data = {"name": "name", "extra": "value"}
    resource = Resource.from_dict(data)
    assert resource.name == "name"
    assert resource.custom["extra"] == "value"
    assert resource.to_dict() == {
        "$schema": settings.PROFILE_CURRENT_RESOURCE,
        "name": "name",
        "extra": "value",
    }


def test_model_to_path(tmp_path: Path):
    path = str(tmp_path / "resource.json")
    resource = Resource.from_path("data/resource.json")
    resource.to_path(path)
    with open(path) as file:
        assert json.loads(file.read()) == {
            "$schema": settings.PROFILE_CURRENT_RESOURCE,
            "name": "name",
            "path": "table.csv",
        }


def test_model_from_path_emtpy_file():
    with pytest.raises(Error) as excinfo:
        Resource.from_path("data/empty.json")
    error = excinfo.value
    assert str(error) == "The file is empty: data/empty.json"


def test_model_from_path_missing_file():
    with pytest.raises(Error) as excinfo:
        Resource.from_path("data/missing.json")
    error = excinfo.value
    assert str(error) == 'Cannot read file "data/missing.json"'


def test_model_from_path_not_supported_format():
    with pytest.raises(Error) as excinfo:
        Resource.from_path("data/text.txt")
    error = excinfo.value
    assert str(error) == "Cannot load data from text with format: txt"


def test_model_from_path_yaml():
    resource = Resource.from_path("data/resource.yaml")
    assert resource.name == "name"
    assert resource.path == "table.csv"


def test_model_to_path_yaml(tmp_path: Path):
    path = str(tmp_path / "resource.yaml")
    resource = Resource.from_path("data/resource.json")
    resource.to_path(path)
    with open(path) as file:
        assert yaml.safe_load(file.read()) == {
            "$schema": settings.PROFILE_CURRENT_RESOURCE,
            "name": "name",
            "path": "table.csv",
        }


def test_model_get_entity_from_package_supports_relative_and_prefixed_paths():
    resource = Resource(name="sales-table", path="sales.csv")
    package = Package(name="sales-dataset", resources=[resource])

    assert package.get_entity("sales-table") is resource
    assert package.get_entity("sales-dataset.sales-table") is resource


def test_model_get_entity_from_catalog_traverses_nested_catalogs_and_packages():
    resource = Resource(name="sales-table", path="sales.csv")
    package = Package(name="sales-dataset", resources=[resource])
    archive_resource = Resource(name="notes", path="notes.md")
    archive = Catalog(name="archive", resources=[archive_resource])
    catalog = Catalog(name="warehouse", packages=[package], catalogs=[archive])

    assert catalog.get_entity("sales-dataset.sales-table") is resource
    assert catalog.get_entity("warehouse.sales-dataset.sales-table") is resource
    assert catalog.get_entity("archive.notes") is archive_resource
    assert archive.get_entity("archive.notes") is archive_resource


def test_model_iter_entity_references_uses_any_named_parent_path():
    resource = Resource(name="sales-table", path="sales.csv")
    package = Package(name="sales-dataset", resources=[resource])
    catalog = Catalog(name="warehouse", packages=[package])

    references = dict(catalog.iter_entity_references(include_self=True))

    assert references["warehouse"] is catalog
    assert references["warehouse.sales-dataset"] is package
    assert references["warehouse.sales-dataset.sales-table"] is resource
