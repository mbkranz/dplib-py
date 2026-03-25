import pytest
from pydantic import ValidationError

from dplib import settings
from dplib.models import Catalog, Package, Resource


def test_catalog_from_path():
    catalog = Catalog.from_path("data/catalog.json")
    assert len(catalog.packages) == 1
    assert catalog.packages[0].name == "name"
    assert len(catalog.packages[0].resources) == 1
    assert catalog.packages[0].resources[0].name == "name"
    assert catalog.packages[0].resources[0].path == "table.csv"


def test_catalog_from_path_full():
    catalog = Catalog.from_path("data/catalog-full.json")
    assert catalog.name == "name"
    assert catalog.title == "title"
    assert catalog.description == "description"
    assert len(catalog.packages) == 2
    assert catalog.packages[0].name == "first"
    assert catalog.packages[1].name == "second"


def test_catalog_from_text():
    text = '{"name": "name"}'
    catalog = Catalog.from_text(text, format="json")
    assert catalog.name == "name"


def test_catalog_from_dict():
    data = {"name": "name"}
    catalog = Catalog.from_dict(data)
    assert catalog.name == "name"


def test_catalog_from_dict_invalid():
    data = {"name": 1}
    with pytest.raises(ValidationError):
        Catalog.from_dict(data)


def test_catalog_set_property_invalid():
    catalog = Catalog()
    with pytest.raises(ValidationError):
        catalog.name = 1  # type: ignore


def test_catalog_get_package():
    catalog = Catalog.from_path("data/catalog.json")
    package = catalog.get_package(name="name")
    assert package is not None
    assert package.name == "name"


def test_catalog_get_package_not_found():
    catalog = Catalog.from_path("data/catalog.json")
    package = catalog.get_package(name="missing")
    assert package is None


def test_catalog_get_entity_package():
    catalog = Catalog.from_path("data/catalog-full.json")
    entity = catalog.get_entity("first")
    assert isinstance(entity, Package)
    assert entity.name == "first"


def test_catalog_get_entity_resource():
    catalog = Catalog.from_path("data/catalog-full.json")
    entity = catalog.get_entity("first.resource1")
    assert isinstance(entity, Resource)
    assert entity.name == "resource1"


def test_catalog_get_entity_resource_second_package():
    catalog = Catalog.from_path("data/catalog-full.json")
    entity = catalog.get_entity("second.resource2")
    assert isinstance(entity, Resource)
    assert entity.name == "resource2"


def test_catalog_get_entity_not_found():
    catalog = Catalog.from_path("data/catalog.json")
    entity = catalog.get_entity("missing")
    assert entity is None


def test_catalog_get_entity_resource_not_found():
    catalog = Catalog.from_path("data/catalog-full.json")
    entity = catalog.get_entity("first.missing")
    assert entity is None


def test_catalog_add_package():
    catalog = Catalog()
    catalog.add_package(Package(name="name"))
    package = catalog.get_package(name="name")
    assert package is not None
    assert package.name == "name"


def test_catalog_to_dict():
    catalog = Catalog()
    assert catalog.to_dict() == {
        "$schema": settings.PROFILE_CURRENT_CATALOG,
    }
    catalog.add_package(Package(name="name"))
    assert catalog.to_dict() == {
        "$schema": settings.PROFILE_CURRENT_CATALOG,
        "packages": [{"name": "name"}],
    }
