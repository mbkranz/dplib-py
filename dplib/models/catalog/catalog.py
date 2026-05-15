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

    def get_entity(self, full_name: str) -> Optional[Union[Resource, Package, "Catalog"]]:
        """
        Get an entity (Resource, Package, or Catalog) by its name, returning the first match.
        Supports dot notation to traverse nested catalogs and packages.

        For example: `catalog.get_entity("data-warehouse.sales-dataset.sales-table")`

        Parameters:
            full_name: The name or dot-path of the entity to retrieve

        Returns:
            The matched entity, or None if not found.
        """
        if not full_name:
            return None

        parts = full_name.split(".", 1)
        current_part = parts[0]
        remainder = parts[1] if len(parts) > 1 else None

        # Search the current level
        match: Optional[Union[Resource, Package, "Catalog"]] = None
        
        for item in self.resources:
            if isinstance(item, Resource) and item.name == current_part:
                match = item
                break
                
        if not match:
            for item in self.packages:
                if isinstance(item, Package) and item.name == current_part:
                    match = item
                    break

        if not match:
            for item in self.catalogs:
                if isinstance(item, Catalog) and item.name == current_part:
                    match = item
                    break

        if not match:
            return None

        # If there is no remaining path, we found our target
        if not remainder:
            return match

        # If there is a remaining path, the match MUST be a container (Catalog or Package)
        # to continue the traversal.
        if isinstance(match, Catalog):
            return match.get_entity(remainder)
            
        if isinstance(match, Package):
            # A standard Package only allows resources inside it, so we stop recursing.
            # If the remainder still has dots, a default standard Package cannot resolve it.
            if "." in remainder:
                return None 
            return match.get_resource(name=remainder)

        return None


Catalog.model_rebuild()