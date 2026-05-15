from typing import List, Union, Optional
import pydantic

from ...system import Model
from ..resource import Resource
from ..package import Package


class Catalog(Model):
    """
    A Catalog represents a registry, library, or folder. It is a collection of 
    entirely independent datasets, resources, or nested catalogs. Unlike a Package 
    (which bounds a single logical cohesive dataset), a Catalog is a structural container.
    """
    profile: str = pydantic.Field(
        default="data-package-catalog",
        alias="$schema",
    )
    
    # --- Metadata ---
    
    name: Optional[str] = None
    """
    A short url-usable (and preferably human-readable) name.
    """

    title: Optional[str] = None
    """
    A human-oriented title of the catalog.
    """

    description: Optional[str] = None
    """
    A description of the catalog. The description MUST be markdown formatted.
    """

    basepath: Optional[str] = pydantic.Field(default=None, exclude=True)
    """
    A basepath of the catalog.
    """

    # --- Contents ---

    resources: List[Union[Resource, dict]] = []
    packages: List[Union[Package, dict]] = []
    catalogs: List[Union["Catalog", dict]] = []

    # --- Methods ---

    def get_package(self, *, name: str) -> Optional[Package]:
        """Get package by name"""
        for pkg in self.packages:
            if isinstance(pkg, Package) and pkg.name == name:
                return pkg
        return None
        
    def get_resource(self, *, name: str) -> Optional[Resource]:
        """Get resource by name"""
        for res in self.resources:
            if isinstance(res, Resource) and res.name == name:
                return res
        return None

Catalog.model_rebuild()