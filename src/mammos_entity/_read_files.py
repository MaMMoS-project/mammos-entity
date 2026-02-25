from __future__ import annotations

import csv
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import h5py
import mammos_units as u
import pandas as pd
import yaml

from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection

if TYPE_CHECKING:
    import mammos_entity


_YAML_V1_LEAF_KEYS = {"ontology_label", "ontology_iri", "unit", "value"}
_YAML_V2_ENTITY_KEYS = {
    "ontology_label",
    "description",
    "ontology_iri",
    "unit",
    "value",
}
_YAML_V2_QUANTITY_KEYS = {"unit", "value"}
_YAML_V2_VALUE_KEYS = {"value"}


def _format_yaml_path_segment(name: str) -> str:
    r"""Format one key name for a dotted YAML error path.

    Names containing ``.`` or ``"`` are wrapped in double quotes and escaped so
    the logical path stays unambiguous.

    Examples:
        ``dotted.key`` -> ``"dotted.key"``
        ``a"b`` -> ``"a\"b"``
    """
    if "." in name or '"' in name:
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return name


def _join_yaml_path(parent_path: str, name: str) -> str:
    """Append one key name to a logical YAML path used in error messages.

    The appended segment is first normalized with :func:`_format_yaml_path_segment`.

    Examples:
        ``("", "Ms")`` -> ``"Ms"``
        ``("outer", "dotted.key")`` -> ``outer."dotted.key"``
    """
    segment = _format_yaml_path_segment(name)
    if not parent_path:
        return segment
    return f"{parent_path}.{segment}"


def _display_collection_path(path: str) -> str:
    """Return a user-facing collection label for error messages.

    An empty path is rendered as ``top-level collection``.
    """
    return path if path else "top-level collection"


def _validate_yaml_entity_name(name: object, collection_path: str) -> str:
    """Validate one entry name within a YAML collection.

    The name must be a string and must not be ``description`` because that key
    is reserved for collection metadata.
    """
    displayed_collection_path = _display_collection_path(collection_path)
    if not isinstance(name, str):
        raise RuntimeError(
            f'Entry names in collection "{displayed_collection_path}" must be '
            "strings in mammos yaml, "
            f"found {name!r} ({type(name).__name__})."
        )
    if name == "description":
        raise RuntimeError(
            'Entry name "description" is reserved in mammos yaml and cannot '
            f'be used inside collection "{displayed_collection_path}".'
        )
    return name


def from_csv(filename: str | Path) -> mammos_entity.EntityCollection:
    """Read MaMMoS CSV file.

    The required file format is described in
    :py:func:`~mammos_entity.EntityCollection.to_csv`.

    Args:
        filename: Name of the file to read. The file is read as CSV no matter the file
            extension.

    Returns:
        A collection object providing access to all entities saved in the file.

    .. seealso:: :py:func:`mammos_entity.EntityCollection.to_csv`
    """
    with open(filename, newline="") as csvfile:
        file_version_information = csvfile.readline()

        try:
            version = re.search(r"v\d+", file_version_information)
        except StopIteration:
            raise RuntimeError(f"Trying to read empty file: {filename}") from None

        if not version:
            raise RuntimeError(
                f"Cannot read version information from file {filename}. "
                f"Content of the first line: '{file_version_information}'"
            )
            raise RuntimeError("File does not have version information in line 1.")
        if version.group() not in [f"v{i}" for i in range(1, 4)]:
            raise RuntimeError(
                f"Reading mammos csv {version.group()} is not supported."
            )
        else:
            version_number = int(version.group().lstrip("v"))

        collection_description = []

        # read description
        position = csvfile.tell()
        if "#--" in next(csvfile):
            while True:
                line = next(csvfile)
                if "#--" in line:
                    break
                else:
                    collection_description.append(line.removeprefix("# ").strip())
        else:
            # reset the file position
            csvfile.seek(position)

        # read ontology metadata
        if version_number >= 3:
            reader = csv.reader(
                csvfile,
                delimiter=",",
                quoting=csv.QUOTE_MINIMAL,
                lineterminator=os.linesep,
            )
            ontology_labels = next(reader)
            descriptions = next(reader)
            ontology_iris = next(reader)
            units = next(reader)
        else:
            ontology_labels = csvfile.readline().strip().removeprefix("#").split(",")
            descriptions = [""] * len(ontology_labels)
            ontology_iris = csvfile.readline().strip().removeprefix("#").split(",")
            units = csvfile.readline().strip().removeprefix("#").split(",")

        data = pd.read_csv(csvfile)
        names = data.keys()
        scalar_data = len(data) == 1

    entities = {}
    for name, ontology_label, description, iri, unit in zip(
        names, ontology_labels, descriptions, ontology_iris, units, strict=True
    ):
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            entity = Entity(
                ontology_label=ontology_label,
                value=data_values,
                unit=unit,
                description=description,
            )
            _check_iri(entity, iri)
            entities[name] = entity
        elif unit:
            entities[name] = u.Quantity(data_values, unit)
        else:
            entities[name] = data_values

    return EntityCollection(description="\n".join(collection_description), **entities)


def from_yaml(filename: str | Path) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file.

    This function can read mammos yaml v1 and v2. The required file format is described
    in :py:func:`~mammos_entity.EntityCollection.to_yaml`.

    Args:
        filename: Name of the file to read. The file is read as YAML no matter the file
            extension.

    Returns:
        A collection object providing access to all entities saved in the file.

    .. seealso:: :py:func:`mammos_entity.EntityCollection.to_yaml`
    """
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if not isinstance(file_content, Mapping):
        raise RuntimeError("YAML files must contain a top-level mapping.")

    if (
        "metadata" not in file_content
        or not isinstance(file_content["metadata"], Mapping)
        or "version" not in file_content["metadata"]
    ):
        raise RuntimeError("File does not have a key metadata:version.")

    version = file_content["metadata"]["version"]

    if version == "v1":
        if set(file_content.keys()) != {"metadata", "data"}:
            raise RuntimeError(
                "mammos yaml v1 files must have exactly two top-level keys, "
                "'metadata' and 'data'."
            )
        if not isinstance(file_content["data"], Mapping):
            raise RuntimeError("'data' must be a mapping.")
        return _from_yaml_v1(file_content)
    elif version == "v2":
        if set(file_content.keys()) != {"metadata", "description", "data"}:
            raise RuntimeError(
                "mammos yaml v2 files must have exactly three top-level keys, "
                "'metadata', 'description' and 'data'."
            )
        if not isinstance(file_content["data"], Mapping):
            raise RuntimeError("'data' must be a mapping.")
        root = {
            "description": file_content["description"],
            "data": file_content["data"],
        }
        return _parse_yaml_collection_v2(root, "")
    else:
        raise RuntimeError(f"Reading mammos yaml {version} is not supported.")


def _parse_yaml_leaf_v1(item: Mapping, key: str):
    """Parse one v1 leaf node into Entity/Quantity/plain value."""
    if not isinstance(item, Mapping):
        raise RuntimeError(
            f"Element '{key}' must be a mapping, found {type(item).__name__}."
        )

    if set(item.keys()) != _YAML_V1_LEAF_KEYS:
        raise RuntimeError(
            f"Element '{key}' does not have the required keys,"
            f" expected {_YAML_V1_LEAF_KEYS}, found {list(item.keys())}."
        )

    if item["ontology_label"] is not None:
        entity = Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
            description="",
        )
        _check_iri(entity, item["ontology_iri"])
        return entity
    if item["unit"] is not None:
        return u.Quantity(item["value"], item["unit"])
    return item["value"]


def _from_yaml_v1(file_content: dict) -> mammos_entity.EntityCollection:
    """Parse a full mammos yaml v1 document."""
    collection_description = file_content["metadata"].get("description", "")
    if collection_description is None:
        collection_description = ""
    elif not isinstance(collection_description, str):
        raise RuntimeError(
            "Element 'metadata:description' must be a string or null in "
            "mammos yaml v1, "
            f"found {type(collection_description).__name__}."
        )

    collection = EntityCollection(description=collection_description)
    for key, item in file_content["data"].items():
        key = _validate_yaml_entity_name(key, "")
        collection[key] = _parse_yaml_leaf_v1(item, key)
    return collection


def _parse_yaml_leaf_v2(item: Mapping, entry_path: str):
    """Parse one v2 entity-like node into an Entity/Quantity/vale object."""
    if not isinstance(item, Mapping):
        raise RuntimeError(
            f'Entry "{entry_path}" in a collection must be a mapping, found '
            f"{type(item).__name__}."
        )

    keys = set(item)

    if "value" not in keys:
        raise RuntimeError(
            f'Entry "{entry_path}" is an entity-like entry in a collection and '
            "must contain key 'value' for mammos yaml v2."
        )

    unknown_keys = keys - _YAML_V2_ENTITY_KEYS
    if unknown_keys:
        raise RuntimeError(
            f'Entry "{entry_path}" is an entity-like entry in a collection and '
            "contains unknown keys for mammos yaml v2: "
            f"{sorted(unknown_keys)}."
        )

    if "ontology_label" in keys:
        missing = _YAML_V2_ENTITY_KEYS - keys
        if missing:
            raise RuntimeError(
                f'Entry "{entry_path}" is an Entity entry in a collection and '
                "is missing required keys for mammos yaml v2: "
                f"{sorted(missing)}."
            )
        entity = Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
            description=item["description"],
        )
        _check_iri(entity, item["ontology_iri"])
        return entity

    if keys == _YAML_V2_QUANTITY_KEYS:
        return u.Quantity(item["value"], item["unit"])

    if keys == _YAML_V2_VALUE_KEYS:
        return item["value"]

    raise RuntimeError(
        f'Entry "{entry_path}" is an entity-like entry in a collection and has '
        f"invalid keys for mammos yaml v2: {sorted(keys)}."
    )


def _parse_yaml_collection_v2(node: Mapping, collection_path: str) -> EntityCollection:
    """Parse one v2 collection node recursively."""
    if set(node.keys()) != {"description", "data"}:
        raise RuntimeError(
            f'Collection "{_display_collection_path(collection_path)}" must have '
            'exactly keys "description" and "data" in mammos yaml v2.'
        )

    description = node["description"]
    if not isinstance(description, str):
        raise RuntimeError(
            f'Collection "{_display_collection_path(collection_path)}" must have '
            "a string 'description' in "
            f"mammos yaml v2, found {type(description).__name__}."
        )

    if not isinstance(node["data"], Mapping):
        raise RuntimeError(
            f'Collection "{_display_collection_path(collection_path)}" must have '
            "a mapping 'data' in mammos yaml v2, "
            f"found {type(node['data']).__name__}."
        )

    collection = EntityCollection(description=description)
    for name, item in node["data"].items():
        name = _validate_yaml_entity_name(name, collection_path)
        entry_path = _join_yaml_path(collection_path, name)

        if isinstance(item, Mapping) and set(item.keys()) == {"description", "data"}:
            collection[name] = _parse_yaml_collection_v2(item, entry_path)
        else:
            collection[name] = _parse_yaml_leaf_v2(item, entry_path)
    return collection


def _check_iri(entity: mammos_entity.Entity, iri: str) -> None:
    """Check that iri points to entity.

    Raises:
        RuntimeError: if the given iri and the entity iri are different.
    """
    if entity.ontology.iri != iri:
        raise RuntimeError(
            f"Incompatible IRI for {entity!r}, expected: '{entity.ontology.iri}',"
            f" got '{iri}'."
        )


def from_hdf5(
    element: h5py.File | h5py.Group | h5py.Dataset | str | os.PathLike,
    decode_bytes: bool = True,
) -> mammos_entity.EntityLike | mammos_entity.EntityCollection:
    """Read HDF5 file, group or dataset and convert to Entity or EntityCollection.

    Datasets are converted to :py:class:`~mammos_entity.Entity`,
    :py:class:`~astropy.units.Quantity`, or a numpy array or other builtin datatype
    depending on their associated metadata and shape.

    Groups are converted to :py:class:`~mammos_entity.EntityCollection`. Arbitrary
    nesting of groups is supported and produces nested collections.

    Args:
        element: If it is a `str` or `PathLike` the entire file is read from disk. If
            it is an open HDF5 `File`, `Group` or `Dataset` only that part of the file
            is read.
        decode_bytes: If ``True`` data of all datasets of type object is converted to
            strings (if scalar) or numpy arrays of strings (if vector). If ``False`` the
            bytes object (or array of bytes objects) is returned.

    Returns:
        All data in the given HDF5 file/group/dataset as (nested) EntityCollection
        and/or EntityLike object.


    .. seealso::

       :py:func:`mammos_entity.Entity.to_hdf5`
       :py:func:`mammos_entity.EntityCollection.to_hdf5`
    """
    if isinstance(element, str | os.PathLike):
        with h5py.File(element) as f:
            return from_hdf5(f, decode_bytes)
    elif isinstance(element, h5py.File | h5py.Group):
        collection = EntityCollection(description=element.attrs.get("description", ""))
        for name, sub in element.items():
            collection[name] = from_hdf5(sub)
        return collection
    elif "ontology_label" in element.attrs:
        return Entity(
            ontology_label=element.attrs["ontology_label"],
            value=element[()],
            unit=element.attrs["unit"],
            description=element.attrs["description"],
        )
    elif "unit" in element.attrs:
        return u.Quantity(element[()], element.attrs["unit"])
    else:
        if element.dtype == "object" and decode_bytes:
            element = element.asstr()
        data = element[()]
        return data
