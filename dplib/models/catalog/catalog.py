from __future__ import annotations

from typing import List, Optional, Union

import pydantic

from ... import settings
from ...system import Model
from ..package import Package
from ..resource import Resource


class Catalog(Model):
    """Data Catalog model

    A Data Catalog is a collection of Data Packages. It provides a way to
    group and manage multiple packages together, with support for accessing
    packages and their resources using dot notation via ``get_entity``.
    """

    profile: str = pydantic.Field(
        default=settings.PROFILE_CURRENT_CATALOG,
        alias="$schema",
    )
    """A profile URL"""

    name: Optional[str] = None
    """
    A short url-usable (and preferably human-readable) name of the catalog.
    This MUST be lower-case and contain only alphanumeric characters
    along with ".", "_" or "-" characters.
    """

    title: Optional[str] = None
    """
    A string providing a title or one sentence description for this catalog.
    """

    description: Optional[str] = None
    """
    A description of the catalog. The description MUST be markdown formatted —
    this also allows for simple plain text as plain text is itself valid markdown.
    """

    packages: List[Package] = pydantic.Field(default_factory=list)
    """
    List of Data Packages in the catalog.
    """

    # Getters

    def get_package(self, *, name: str) -> Optional[Package]:
        """Get a package by name

        Parameters:
            name: The name of the package

        Returns:
            The package if found
        """
        for package in self.packages:
            if package.name == name:
                return package

    def get_entity(self, full_name: str) -> Optional[Union[Package, Resource]]:
        """Get a package or resource by full name using dot notation

        Parameters:
            full_name: The full name of the entity. Use dot notation to access
                       a resource within a package
                       (e.g., ``"package_name.resource_name"``).
                       Omit the dot to retrieve a package by name
                       (e.g., ``"package_name"``).

        Returns:
            The package or resource if found
        """
        parts = full_name.split(".", 1)
        package = self.get_package(name=parts[0])
        if package is None:
            return None
        if len(parts) == 1:
            return package
        return package.get_resource(name=parts[1])

    # Setters

    def add_package(self, package: Package) -> None:
        """Add a package to the catalog

        Parameters:
            package: The package to add
        """
        self.packages.append(package)

    # Converters

    def to_dict(self):
        data = {"$schema": settings.PROFILE_CURRENT_CATALOG}
        data.update(super().to_dict())
        return data
