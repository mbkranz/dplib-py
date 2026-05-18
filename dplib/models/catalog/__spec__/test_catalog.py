import pytest

from dplib.models import Catalog, Dialect, Package, Resource, Schema


def test_catalog_from_path():
    catalog = Catalog.from_path("data/catalog.json")
    assert catalog.name == "name"
    assert catalog.title == "title"
    assert len(catalog.packages) == 1


def test_catalog_dereference():
    catalog = Catalog.from_path("data/catalog.json")
    catalog.dereference()
    package = catalog.get_package(name="name")
    assert package
    resource = package.get_resource(name="name")
    assert resource
    assert isinstance(resource.dialect, Dialect)
    assert resource.dialect.delimiter == ";"
    assert isinstance(resource.schema, Schema)
    assert len(resource.schema.fields) == 2


def test_catalog_dereference_nested():
    inner = Catalog(name="inner", packages=[Package.from_path("data/package-full.json")])
    outer = Catalog(name="outer", catalogs=[inner])
    outer.dereference()
    package = outer.catalogs[0].get_package(name="name")
    assert package
    resource = package.get_resource(name="name")
    assert resource
    assert isinstance(resource.dialect, Dialect)
    assert isinstance(resource.schema, Schema)


def test_catalog_dereference_package_by_path():
    catalog = Catalog.from_path("data/catalog-paths.json")
    assert catalog.packages[0].path == "package-full.json"
    catalog.dereference()
    package = catalog.get_package(name="name")
    assert package
    assert package.path is None
    resource = package.get_resource(name="name")
    assert resource
    assert isinstance(resource.dialect, Dialect)
    assert isinstance(resource.schema, Schema)


def test_catalog_dereference_catalog_by_path():
    catalog = Catalog.from_path("data/catalog-paths.json")
    assert catalog.catalogs[0].path == "sub-catalog.json"
    catalog.dereference()
    sub = catalog.catalogs[0]
    assert sub.name == "sub"
    assert sub.path is None
    package = sub.get_package(name="name")
    assert package
    resource = package.get_resource(name="name")
    assert resource
    assert isinstance(resource.dialect, Dialect)
    assert isinstance(resource.schema, Schema)


def test_catalog_getters_support_relative_entity_references():
    catalog = Catalog(
        name="warehouse",
        packages=[Package(name="sales", resources=[Resource(name="table", path="table.csv")])],
        catalogs=[
            Catalog(
                name="archive",
                packages=[Package(name="sales", resources=[])],
                catalogs=[Catalog(name="old")],
            )
        ],
    )
    assert catalog.get_package(name="archive.sales")
    assert catalog.get_resource(name="sales.table")
    assert catalog.get_catalog(name="archive.old")


def test_catalog_getters_raise_for_wrong_entity_type():
    catalog = Catalog(
        name="warehouse",
        packages=[Package(name="sales", resources=[Resource(name="table", path="table.csv")])],
    )
    with pytest.raises(ValueError, match="expected 'resource'"):
        catalog.get_resource(name="sales")
    with pytest.raises(ValueError, match="expected 'package'"):
        catalog.get_package(name="sales.table")
    with pytest.raises(ValueError, match="expected 'catalog'"):
        catalog.get_catalog(name="sales")
    with pytest.raises(ValueError, match="expected 'catalog'"):
        catalog.get_catalog(name="sales.table")
