from __future__ import annotations

from typing import List, Union

from ... import types
from ...errors.metadata import MetadataError
from ...helpers.dict import read_dict
from ...helpers.path import infer_basepath
from ...models import Catalog
from ..metadata.check import check_metadata


def check_catalog(catalog: Union[str, types.IDict, Catalog]) -> List[MetadataError]:
    """Check the validity of a Data Catalog descriptor

    This validates the descriptor against the JSON Schema profiles to ensure
    conformity with the Data Catalog standard.

    Parameters:
        catalog: The Data Catalog descriptor

    Returns:
        A list of errors
    """
    if isinstance(catalog, str):
        catalog = read_dict(catalog)
    if isinstance(catalog, Catalog):
        catalog = catalog.to_dict()

    # Validate
    errors = check_metadata(catalog, type="catalog")

    return errors
