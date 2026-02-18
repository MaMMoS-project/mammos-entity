from __future__ import annotations

import csv
import os
import re
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
        file_content = yaml.safe_load(f)

    if not file_content or list(file_content.keys()) != ["metadata", "data"]:
        raise RuntimeError(
            "YAML files must have exactly two top-level keys, 'metadata' and 'data'."
        )

    if not file_content["metadata"] or "version" not in file_content["metadata"]:
        raise RuntimeError("File does not have a key metadata:version.")

    if (version := file_content["metadata"]["version"]) not in [
        f"v{i}" for i in range(1, 3)
    ]:
        raise RuntimeError(f"Reading mammos yaml {version} is not supported.")
    else:
        version_number = int(version.lstrip("v"))

    collection_description = file_content["metadata"]["description"] or ""

    if not file_content["data"]:
        raise RuntimeError("'data' does not contain anything.")

    if version_number >= 2:
        req_subkeys = {"ontology_label", "description", "ontology_iri", "unit", "value"}
    else:
        req_subkeys = {"ontology_label", "ontology_iri", "unit", "value"}

    entities = {}
    for key, item in file_content["data"].items():
        if set(item) != req_subkeys:
            raise RuntimeError(
                f"Element '{key}' does not have the required keys,"
                f" expected {req_subkeys}, found {list(item)}."
            )
        if item["ontology_label"] is not None:
            entity = Entity(
                ontology_label=item["ontology_label"],
                value=item["value"],
                unit=item["unit"],
                description=item.get("description", ""),
            )
            _check_iri(entity, item["ontology_iri"])
            entities[key] = entity
        elif item["unit"] is not None:
            entities[key] = u.Quantity(item["value"], item["unit"])
        else:
            entities[key] = item["value"]

    return EntityCollection(description=collection_description, **entities)


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
