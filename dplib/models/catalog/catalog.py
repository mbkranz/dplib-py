from typing import List, Union, Optional
import pydantic

from ...helpers.path import assert_safe_path
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

    path: Optional[str] = None
    """
    A path to an external catalog descriptor file (relative to basepath).
    When set, this acts as a stub reference; calling dereference() on the
    parent catalog will load and replace this entry with the full catalog
    from the file.
    """

    # --- Contents ---

    resources: List["Resource"] = []
    packages: List["Package"] = []
    catalogs: List["Catalog"] = []

    def model_post_init(self, _):
        if self.basepath is None:
            return
        for resource in self.resources:
            resource.basepath = self.basepath

        for package in self.packages:
            package.basepath = self.basepath
            package.model_post_init(None)  # re-propagate basepath to package's resources

        for catalog in self.catalogs:
            catalog.basepath = self.basepath
            catalog.model_post_init(None)  # re-propagate basepath recursively
    def get_package(self, *, name: str) -> Optional["Package"]:
        """Get package by name"""
        for pkg in self.packages:
            if isinstance(pkg, Package) and pkg.name == name:
                return pkg
        return None
        
    def get_resource(self, *, name: str) -> Optional["Resource"]:
        """Get resource by name"""
        for res in self.resources:
            if isinstance(res, Resource) and res.name == name:
                return res
        return None
    
    
    def dereference(self) -> "Catalog":
        """Recursively dereference all nested catalogs, packages, and resources.

        For items whose `path` is set, the stub is replaced with the full model
        loaded from that file (resolved against self.basepath). Otherwise each
        item's own dereference() is called in-place to resolve dialects/schemas.
        """
        for resource in self.resources:
            resource.dereference()

        for i, package in enumerate(self.packages):
            if package.path:
                assert_safe_path(package.path, basepath=self.basepath)
                self.packages[i] = Package.from_path(package.path, basepath=self.basepath)
                self.packages[i].dereference()
            else:
                package.dereference()

        for i, catalog in enumerate(self.catalogs):
            if catalog.path:
                assert_safe_path(catalog.path, basepath=self.basepath)
                self.catalogs[i] = Catalog.from_path(catalog.path, basepath=self.basepath)
                self.catalogs[i].dereference()
            else:
                catalog.dereference()

        return self

Catalog.model_rebuild()