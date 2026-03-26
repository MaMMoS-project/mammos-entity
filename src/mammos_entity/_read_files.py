from __future__ import annotations

import csv
import os
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING

import h5py
import mammos_units as u
import pandas as pd
import yaml

from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection

if TYPE_CHECKING:
    import mammos_units
    import numpy

    import mammos_entity


def from_csv(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
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
        version = re.search(r"v\d+", file_version_information)
        if version is None:
            raise RuntimeError(
                f"Cannot read version information from file {filename}. "
                f"Content of the first line: '{file_version_information}'"
            )

        if version.group() not in [f"v{i}" for i in range(1, 4)]:
            raise RuntimeError(
                f"Reading mammos csv {version.group()} is not supported."
            )
        version_number = int(version.group().lstrip("v"))

        collection_description = []

        # read description
        position = csvfile.tell()
        if csvfile.readline().startswith("#--"):
            while True:
                line = csvfile.readline()
                if line == "":
                    raise RuntimeError(
                        "CSV description block is not terminated by a closing dashed "
                        "line."
                    )
                if line.startswith("#--"):
                    break
                else:
                    collection_description.append(
                        line.removeprefix("# ").rstrip("\r\n")
                    )
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
            try:
                ontology_labels = next(reader)
                descriptions = next(reader)
                next(reader)  # ignore IRIs
                units = next(reader)
            except StopIteration as exc:
                raise RuntimeError(
                    "CSV metadata is incomplete. Expected four metadata rows before "
                    "the data table."
                ) from exc
        else:
            metadata_rows = [csvfile.readline() for _ in range(3)]
            if any(row == "" for row in metadata_rows):
                raise RuntimeError(
                    "CSV metadata is incomplete. Expected three metadata rows before "
                    "the data table."
                )
            ontology_labels = metadata_rows[0].strip().removeprefix("#").split(",")
            # ignore IRIs: metadata_rows[1]
            units = metadata_rows[2].strip().removeprefix("#").split(",")
            descriptions = [""] * len(ontology_labels)

        try:
            data = pd.read_csv(csvfile)
        except pd.errors.EmptyDataError as exc:
            raise RuntimeError("CSV data table is empty.") from exc
        names = data.keys()
        scalar_data = len(data) == 1

    try:
        columns = list(zip(names, ontology_labels, descriptions, units, strict=True))
    except ValueError as exc:
        raise RuntimeError(
            "CSV metadata columns and data columns do not match."
        ) from exc

    collection = EntityCollection(description="\n".join(collection_description))
    for name, ontology_label, description, unit in columns:
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            entity = Entity(
                ontology_label=ontology_label,
                value=data_values,
                unit=unit,
                description=description,
            )
            collection[name] = entity
        elif unit:
            collection[name] = u.Quantity(data_values, unit)
        else:
            collection[name] = data_values

    return collection


def from_yaml(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file.

    The required file format is described in
    :py:func:`~mammos_entity.EntityCollection.to_yaml`.

    Args:
        filename: Name of the file to read. The file is read as YAML no matter the file
            extension.

    Returns:
        A collection object providing access to all entities saved in the file.

    .. seealso:: :py:func:`mammos_entity.EntityCollection.to_yaml`

    """
    with open(filename) as f:
        first_line = f.readline().strip()
    if first_line == "# mammos yaml v2":
        return _from_yaml_v2(filename)
    return _from_yaml_v1(filename)


def _from_yaml_v1(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file v1."""
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if not isinstance(file_content, Mapping):
        raise RuntimeError("mammos yaml v1 files must contain a top-level mapping.")

    if set(file_content.keys()) != {"metadata", "data"}:
        raise RuntimeError(
            "mammos yaml v1 files must have exactly two top-level keys, "
            "'metadata' and 'data'."
        )

    if not (
        "metadata" in file_content
        and isinstance(file_content["metadata"], Mapping)
        and "version" in file_content["metadata"]
        and file_content["metadata"]["version"] == "v1"
    ):
        raise RuntimeError(
            "Wrong mammos yaml v1 syntax. Expected 'metadata' key with "
            "the 'version' equal to 'v1'."
        )

    collection_description = file_content["metadata"].get("description") or ""
    if not isinstance(file_content.get("data"), Mapping):
        raise RuntimeError("'data' must be a mapping.")
    if not file_content["data"]:
        raise RuntimeError("'data' does not contain anything.")
    collection = EntityCollection(description=collection_description)
    for key, item in file_content["data"].items():
        collection[key] = _parse_yaml_leaf_v1(item, key)
    return collection


def _from_yaml_v2(filename: str | os.PathLike) -> mammos_entity.EntityCollection:
    """Read MaMMoS YAML file v2."""
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if not isinstance(file_content, Mapping):
        raise RuntimeError("mammos yaml v2 files must contain a top-level mapping.")

    if set(file_content.keys()) != {"metadata", "description", "data"}:
        raise RuntimeError(
            "mammos yaml v2 files must have exactly three top-level keys, "
            "'metadata', 'description' and 'data'."
        )
    root = {
        "description": file_content["description"],
        "data": file_content["data"],
    }
    return _parse_yaml_collection_v2(root, "")


def _parse_yaml_leaf_v1(item: Mapping, key: str):
    if not isinstance(item, Mapping):
        raise RuntimeError(
            f"Element '{key}' must be a mapping, found {type(item).__name__}."
        )

    keys = set(item)
    v1_keys = {"ontology_label", "ontology_iri", "unit", "value"}

    if keys != v1_keys:
        raise RuntimeError(
            f"Element '{key}' has invalid keys: {sorted(keys)}."
            f" Expected {sorted(v1_keys)}."
        )

    if item["ontology_label"] is not None:
        entity = Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
        )
        return entity
    elif item["unit"] is not None:
        return u.Quantity(item["value"], item["unit"])
    else:
        return item["value"]


def _parse_yaml_leaf_v2(item: Mapping, key: str):
    key_display = key or "top-level collection"
    if not isinstance(item, Mapping):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid entity-like in mammos yaml v2: '
            f"expected a mapping, found {type(item).__name__}."
        )

    keys = set(item)
    entity_keys = {"ontology_label", "description", "ontology_iri", "unit", "value"}
    quantity_keys = {"unit", "value"}
    value_keys = {"value"}

    if keys == entity_keys:
        if not isinstance(item["ontology_label"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v2: '
                f'key "ontology_label" must be a string, found '
                f"{type(item['ontology_label']).__name__}."
            )
        if not isinstance(item["description"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v2: '
                f'key "description" must be a string, found '
                f"{type(item['description']).__name__}."
            )
        if not isinstance(item["ontology_iri"], str):
            raise RuntimeError(
                f'Entry "{key_display}" is an invalid entity-like in mammos yaml v2: '
                f'key "ontology_iri" must be a string, found '
                f"{type(item['ontology_iri']).__name__}."
            )
        entity = Entity(
            ontology_label=item["ontology_label"],
            value=item["value"],
            unit=item["unit"],
            description=item["description"],
        )
        return entity
    elif keys == quantity_keys:
        return u.Quantity(item["value"], item["unit"])
    elif keys == value_keys:
        return item["value"]
    else:
        expected = [sorted(entity_keys), sorted(quantity_keys), sorted(value_keys)]
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid entity-like in mammos yaml v2: '
            f"invalid keys {sorted(keys)}; expected one of {expected}."
        )


def _parse_yaml_collection_v2(node: Mapping, key: str) -> EntityCollection:
    key_display = key or "top-level collection"
    if set(node.keys()) != {"description", "data"}:
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v2: '
            f"invalid keys {sorted(node.keys())}; expected ['data', 'description']."
        )

    description = node["description"]
    if not isinstance(description, str):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v2: '
            f'key "description" must be a string, found {type(description).__name__}.'
        )

    if not isinstance(node["data"], Mapping):
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v2: '
            f'key "data" must be a mapping, found {type(node["data"]).__name__}.'
        )
    if key == "" and not node["data"]:
        raise RuntimeError(
            f'Entry "{key_display}" is an invalid collection in mammos yaml v2: '
            'key "data" does not contain anything.'
        )

    collection = EntityCollection(description=description)
    for name, item in node["data"].items():
        child_path = _join_path(key, name)
        if isinstance(item, Mapping):
            item_keys = set(item.keys())
            leaf_hint_keys = {"ontology_label", "ontology_iri", "unit", "value"}
            # Route ambiguous mappings with collection keys to collection parsing,
            # unless they clearly belong to an entity-like schema.
            if item_keys & leaf_hint_keys:
                collection[name] = _parse_yaml_leaf_v2(item, child_path)
            elif "description" in item_keys or "data" in item_keys:
                collection[name] = _parse_yaml_collection_v2(item, child_path)
            else:
                collection[name] = _parse_yaml_leaf_v2(item, child_path)
        else:
            collection[name] = _parse_yaml_leaf_v2(item, child_path)
    return collection


def _join_path(parent_path: str, segment: str) -> str:
    # In principle there could be name clashes if we have two nested collections:
    # - outer["dotted.inner"].Ms
    # - outer["dotted"]["inner"].Ms
    # In practice this will rarely (never) happen so we ignore it.
    if parent_path:
        return f"{parent_path}.{segment}"
    return segment


def from_hdf5(
    element: h5py.File | h5py.Group | h5py.Dataset | str | os.PathLike,
    decode_bytes: bool = True,
) -> (
    mammos_entity.Entity
    | mammos_units.Quantity
    | numpy.typing.ArrayLike
    | mammos_entity.EntityCollection
):
    """Read HDF5 file, group or dataset and convert to Entity or EntityCollection.

    Datasets are converted to :py:class:`~mammos_entity.Entity`,
    :py:class:`~mammos_units.Quantity`, or a numpy array or other builtin datatype
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
        and/or entity-like object.


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
