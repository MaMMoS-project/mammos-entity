"""Reading submodule.

All the functions in this submodule call specific reading functions from `_io`.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import h5py

import mammos_entity as me

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

        if version.group() not in [f"v{i}" for i in range(1, 5)]:
            raise RuntimeError(f"Reading mammos csv {version.group()} is not supported.")
        version_number = int(version.group().lstrip("v"))

        match version_number:
            case 1:
                return me._io._from_csv_v1(csvfile)
            case 2:
                return me._io._from_csv_v2(csvfile)
            case 3:
                return me._io._from_csv_v3(csvfile)
            case 4:
                return me._io._from_csv_v4(csvfile)


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
    match first_line:
        case "# mammos yaml v2":
            return me._io._from_yaml_v2(filename)
        case "# mammos yaml v3":
            return me._io._from_yaml_v3(filename)
        case _:
            return me._io._from_yaml_v1(filename)


def from_hdf5(
    element: h5py.File | h5py.Group | h5py.Dataset | str | os.PathLike,
    decode_bytes: bool = True,
) -> mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike | mammos_entity.EntityCollection:
    """Read MaMMoS HDF5 file.

    The required file format is described in
    :py:func:`~mammos_entity.EntityCollection.to_hdf5`.

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

    mammos_hdf5_version = element.attrs.get("mammos_hdf5_version", "v1")
    match mammos_hdf5_version:
        case "v1":
            return me._io._from_hdf5_v1(element, decode_bytes)
        case "v2":
            return me._io._from_hdf5_v2(element, decode_bytes)
