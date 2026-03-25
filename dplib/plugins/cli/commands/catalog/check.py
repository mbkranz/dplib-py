from __future__ import annotations

from dplib.actions.catalog.check import check_catalog

from ...helpers.check import print_check_results
from ...options.path import Path
from .main import program


@program.command(name="check")
def command(
    path: str = Path,
):
    """Check the validity of a Data Catalog descriptor."""
    errors = check_catalog(path)
    print_check_results(path, errors)
