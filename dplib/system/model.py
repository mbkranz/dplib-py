from __future__ import annotations

import pprint
import re
import warnings
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel
from typing_extensions import Self

from .. import types
from ..error import Error
from ..helpers.dict import clean_dict, dump_dict, load_dict
from ..helpers.file import read_file, write_file
from ..helpers.path import ensure_basepath, infer_format


ENTITY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class EntityReference:
    """Address a contained catalog/package/resource by name path and JSON Pointer.

    ``name_path`` is the human selector used by CLIs (for example
    ``warehouse.sales.table``). ``json_pointer`` is the exact location in the
    descriptor document using RFC 6901-style collection/index addressing (for
    example ``/packages/0/resources/1``).  The pointer is independent of names,
    while the name path is intentionally constrained so it remains unambiguous
    for dot-path selection.
    """

    name_path: str
    json_pointer: str
    entity_type: str
    model: "Model"
    parent: Optional["Model"]
    collection: Optional[str]
    index: Optional[int]


def _escape_json_pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _join_json_pointer(parent_pointer: str, collection: str, index: int) -> str:
    parts = [
        part
        for part in (
            parent_pointer,
            _escape_json_pointer_segment(collection),
            str(index),
        )
        if part
    ]
    return "/" + "/".join(part.strip("/") for part in parts)


def _model_entity_type(model: "Model", collection: Optional[str] = None) -> str:
    if collection == "resources":
        return "resource"
    if collection == "packages":
        return "package"
    if collection == "catalogs":
        return "catalog"

    model_type = type(model).__name__.lower()
    for suffix in ("resource", "package", "catalog"):
        if model_type.endswith(suffix):
            return suffix
    return "entity"


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

    def _entity_child_slots(self) -> list[tuple[str, int, "Model"]]:
        children: list[tuple[str, int, Model]] = []
        for field_name in ("resources", "packages", "catalogs"):
            value = getattr(self, field_name, None)
            if isinstance(value, list):
                children.extend(
                    (field_name, index, item)
                    for index, item in enumerate(value)
                    if isinstance(item, Model)
                )
            elif isinstance(value, Model):
                children.append((field_name, 0, value))
        return children

    def iter_entity_paths(
        self,
        *,
        include_self: bool = False,
        parent_name_path: Optional[str] = None,
        parent_json_pointer: str = "",
        parent: Optional["Model"] = None,
        collection: Optional[str] = None,
        index: Optional[int] = None,
    ) -> list[EntityReference]:
        """Return contained entity references with both selector and JSON paths."""
        references: list[EntityReference] = []
        current_parent_name_path = parent_name_path

        current_name = getattr(self, "name", None)
        current_name = current_name.strip() if isinstance(current_name, str) else ""
        if current_name:
            current_name_path = (
                current_name
                if parent_name_path is None
                else f"{parent_name_path}.{current_name}"
            )
        else:
            current_name_path = parent_name_path

        if include_self and current_name_path is not None and current_name:
            references.append(
                EntityReference(
                    name_path=current_name_path,
                    json_pointer=parent_json_pointer,
                    entity_type=_model_entity_type(self, collection),
                    model=self,
                    parent=parent,
                    collection=collection,
                    index=index,
                )
            )
            current_parent_name_path = current_name_path

        for child_collection, child_index, child in self._entity_child_slots():
            child_name = getattr(child, "name", None)
            if not isinstance(child_name, str) or not child_name.strip():
                continue

            child_pointer = _join_json_pointer(
                parent_json_pointer, child_collection, child_index
            )
            references.extend(
                child.iter_entity_paths(
                    include_self=True,
                    parent_name_path=current_parent_name_path,
                    parent_json_pointer=child_pointer,
                    parent=self,
                    collection=child_collection,
                    index=child_index,
                )
            )

        return references

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
        return [
            (reference.name_path, reference.model)
            for reference in self.iter_entity_paths(
                include_self=include_self,
                parent_name_path=parent_path,
            )
        ]

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

        references = [
            *self.iter_entity_paths(include_self=True),
            *self.iter_entity_paths(include_self=False),
        ]
        for reference in references:
            if reference.name_path == normalized_name:
                return reference.model

        if "." not in normalized_name:
            for reference in references:
                if reference.name_path.split(".")[-1] == normalized_name:
                    return reference.model

        return None

    def validate_entity_paths(self) -> list[str]:
        """Return descriptor entity path validation errors without raising."""
        errors: list[str] = []
        name_paths: dict[str, str] = {}
        json_pointers: set[str] = set()

        def validate_children(
            parent: Model, parent_name_path: Optional[str], parent_pointer: str
        ) -> None:
            for child_collection, child_index, child in parent._entity_child_slots():
                pointer = _join_json_pointer(
                    parent_pointer, child_collection, child_index
                )
                child_name = getattr(child, "name", None)
                if not isinstance(child_name, str) or not child_name.strip():
                    errors.append(f"Entity at {pointer} must have a non-empty name.")
                    validate_children(child, parent_name_path, pointer)
                    continue

                normalized_name = child_name.strip()
                if not ENTITY_NAME_PATTERN.fullmatch(normalized_name):
                    errors.append(
                        f"Entity name '{normalized_name}' at {pointer} must contain only letters, numbers, hyphens, and underscores."
                    )

                name_path = (
                    normalized_name
                    if parent_name_path is None
                    else f"{parent_name_path}.{normalized_name}"
                )
                existing_pointer = name_paths.get(name_path)
                if existing_pointer is not None:
                    errors.append(
                        f"Entity path '{name_path}' is duplicated at {existing_pointer} and {pointer}."
                    )
                else:
                    name_paths[name_path] = pointer

                if pointer in json_pointers:
                    errors.append(f"JSON pointer '{pointer}' is duplicated.")
                json_pointers.add(pointer)
                validate_children(child, name_path, pointer)

        root_name = getattr(self, "name", None)
        root_path = (
            root_name.strip()
            if isinstance(root_name, str) and root_name.strip()
            else None
        )
        if root_path is not None and not ENTITY_NAME_PATTERN.fullmatch(root_path):
            errors.append(
                f"Entity name '{root_path}' at descriptor root must contain only letters, numbers, hyphens, and underscores."
            )
        validate_children(self, root_path, "")
        return errors

    def assert_valid_entity_paths(self) -> None:
        """Raise an Error if any contained entity path is invalid."""
        errors = self.validate_entity_paths()
        if errors:
            raise Error("Invalid entity paths:\n- " + "\n- ".join(errors))

    @staticmethod
    def get_json_pointer_value(document, pointer: str):
        """Return the value at a JSON Pointer path in a dict/list document."""
        if pointer == "":
            return document

        current = document
        for raw_segment in pointer.strip("/").split("/"):
            segment = raw_segment.replace("~1", "/").replace("~0", "~")
            if isinstance(current, list):
                if not segment.isdigit():
                    raise ValueError(
                        f"JSON pointer segment '{segment}' must be a list index."
                    )
                index = int(segment)
                if index >= len(current):
                    raise ValueError(f"JSON pointer index {index} is out of range.")
                current = current[index]
                continue

            if not isinstance(current, dict):
                raise ValueError(f"Cannot descend into non-object at '{segment}'.")
            if segment not in current:
                raise ValueError(f"JSON pointer segment '{segment}' was not found.")
            current = current[segment]

        return current

    @staticmethod
    def set_property_value(target, property_path: str, value) -> bool:
        """Set a dotted property path on a dict/list document."""
        parts = [part.strip() for part in property_path.split(".") if part.strip()]
        if not parts:
            raise ValueError("Property name must be a non-empty string.")

        current = target
        for segment in parts[:-1]:
            if isinstance(current, list):
                if not segment.isdigit():
                    raise ValueError(
                        f"List segment '{segment}' in property '{property_path}' must be a numeric index."
                    )
                index = int(segment)
                if index >= len(current):
                    raise ValueError(
                        f"List index {index} is out of range for property '{property_path}'."
                    )
                current = current[index]
                continue

            if not isinstance(current, dict):
                raise ValueError(
                    f"Cannot descend into property '{segment}' while updating '{property_path}'."
                )

            next_value = current.get(segment)
            if next_value is None:
                next_value = {}
                current[segment] = next_value
            current = next_value

        leaf = parts[-1]
        if isinstance(current, list):
            if not leaf.isdigit():
                raise ValueError(
                    f"List segment '{leaf}' in property '{property_path}' must be a numeric index."
                )
            index = int(leaf)
            if index >= len(current):
                raise ValueError(
                    f"List index {index} is out of range for property '{property_path}'."
                )
            if current[index] == value:
                return False
            current[index] = value
            return True

        if not isinstance(current, dict):
            raise ValueError(
                f"Cannot set property '{property_path}' on a non-object value."
            )
        if current.get(leaf) == value:
            return False
        current[leaf] = value
        return True

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
