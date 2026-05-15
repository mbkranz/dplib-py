from __future__ import annotations

import pprint
import warnings
from typing import Optional

from pydantic import BaseModel
from typing_extensions import Self

from .. import types
from ..error import Error
from ..helpers.dict import clean_dict, dump_dict, load_dict
from ..helpers.file import read_file, write_file
from ..helpers.path import ensure_basepath, infer_format


class Model(BaseModel, extra="allow", validate_assignment=True):
    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return pprint.pformat(self.to_dict(), sort_dicts=False)

    @property
    def custom(self) -> types.IDict:
        assert self.model_extra is not None
        return self.model_extra

    def entity_children(self) -> list["Model"]:
        """Return named child entities reachable by dot notation.

        By convention, Data Package-style containment is expressed through the
        ``resources``, ``packages``, and ``catalogs`` collections. Any subclass
        exposing one or more of those attributes inherits dot-notation entity
        traversal automatically.
        """
        children: list[Model] = []
        for field_name in ("resources", "packages", "catalogs"):
            value = getattr(self, field_name, None)
            if isinstance(value, list):
                children.extend(item for item in value if isinstance(item, Model))
            elif isinstance(value, Model):
                children.append(value)
        return children

    def iter_entity_references(
        self,
        *,
        include_self: bool = False,
        parent_path: Optional[str] = None,
    ) -> list[tuple[str, "Model"]]:
        """Return child entity selector paths reachable from this model.

        Parameters:
            include_self: Include the current model in the results when it has a
                non-empty ``name``.
            parent_path: Existing selector prefix to prepend to this model and
                all descendants.
        """
        references: list[tuple[str, Model]] = []
        current_parent = parent_path

        current_name = getattr(self, "name", None)
        if include_self and isinstance(current_name, str) and current_name.strip():
            selector_path = (
                current_name if parent_path is None else f"{parent_path}.{current_name}"
            )
            references.append((selector_path, self))
            current_parent = selector_path

        for child in self.entity_children():
            child_name = getattr(child, "name", None)
            if not isinstance(child_name, str) or not child_name.strip():
                continue

            selector_path = (
                child_name if current_parent is None else f"{current_parent}.{child_name}"
            )
            references.append((selector_path, child))
            references.extend(child.iter_entity_references(parent_path=selector_path))

        return references

    def get_entity(self, full_name: str) -> Optional["Model"]:
        """Get a named entity reachable from this model using dot notation.

        The selector may start from the current model's own ``name`` or from
        one of its direct children. For example, if a package is named
        ``sales-dataset``, both ``sales-table`` and
        ``sales-dataset.sales-table`` resolve to the same resource when called
        on that package.
        """
        normalized_name = full_name.strip()
        if not normalized_name:
            return None

        self_name = getattr(self, "name", None)
        if isinstance(self_name, str) and self_name.strip():
            if normalized_name == self_name:
                return self

            prefix = f"{self_name}."
            if normalized_name.startswith(prefix):
                normalized_name = normalized_name[len(prefix):]

        current_part, separator, remainder = normalized_name.partition(".")
        for child in self.entity_children():
            child_name = getattr(child, "name", None)
            if child_name != current_part:
                continue

            if not separator:
                return child

            return child.get_entity(remainder)

        return None

    # Converters

    def to_path(self, path: str, *, format: Optional[str] = None):
        if not format:
            format = infer_format(path, raise_missing=True)
        text = self.to_text(format=format)
        write_file(path, text)

    @classmethod
    def from_path(
        cls, path: str, *, format: Optional[str] = None, basepath: Optional[str] = None
    ) -> Self:
        if not format:
            format = infer_format(path, raise_missing=True)
        path, basepath = ensure_basepath(path, basepath=basepath)
        text = read_file(path)
        if not text:
            raise Error(f"The file is empty: {path}")
        return cls.from_text(text, format=format, basepath=basepath)

    def to_text(self, *, format: str) -> str:
        data = self.to_dict()
        text = dump_dict(data, format=format)
        return text

    @classmethod
    def from_text(cls, text: str, *, format: str, basepath: Optional[str] = None) -> Self:
        data = load_dict(text, format=format)
        return cls.from_dict(data, basepath=basepath)

    def to_dict(self):
        data = self.model_dump(
            mode="json", by_alias=True, exclude_none=True, exclude_defaults=True
        )
        clean_dict(data)
        return data

    @classmethod
    def from_dict(cls, data: types.IDict, *, basepath: Optional[str] = None) -> Self:
        if basepath and cls.model_fields.get("basepath"):
            data["basepath"] = basepath
        return cls(**data)


# Although pydantic@2 moved all the model methods to the "model_" namespace
# the "schema" method is still in the root namespace
# https://github.com/pydantic/pydantic/issues/5165
warnings.filterwarnings(
    action="ignore",
    category=UserWarning,
    module=r"pydantic.*",
    message=r".*schema.*",
)
