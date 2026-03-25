from dplib.actions.catalog.check import check_catalog
from dplib.models import Catalog


def test_check_catalog():
    errors = check_catalog("data/catalog.json")
    assert len(errors) == 0


def test_check_catalog_invalid():
    errors = check_catalog("data/catalog-invalid.json")
    assert len(errors) == 1
    error = errors[0]
    assert error.message == "1 is not of type 'string'"
    assert error.object_path == "/name"


def test_check_catalog_from_model():
    catalog = Catalog(name="name")
    errors = check_catalog(catalog)
    assert len(errors) == 0
