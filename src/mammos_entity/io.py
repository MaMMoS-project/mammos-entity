r"""Support for reading and writing Entity files.

:py:mod:`mammos_entity.io` can write and read data in CSV format.

CSV
===

CSV files written by :py:mod:`mammos_entity.io` contain data in normal CSV format and
additional commented metadata lines at the top of the file. Comment lines start with
``#``, inline comments are not allowed.

The lines are, in order:

- (Commented) the file version in the form ``mammos csv v<VERSION>``
  The reading code checks the version number (using regex v\\d+) to ensure
  compatibility.
- (Commented, optional) a description of the file if given. It will appear delimited by
  dashed lines. It is meant to be human readable and is ignored by reading routines
  in :py:mod:`mammos_entity.io`.
- (Commented) the preferred ontology label.
- (Commented) the ontology IRI.
- (Commented) units.
- The short labels used to refer to individual columns when
  working with the data, e.g. in a :py:class:`pandas.DataFrame`. Omitting spaces in this
  string is advisable.
  Ideally this string is the short ontology label.
- All remaining lines contain data.

Elements in a line are separated by a comma without any surrounding whitespace. A
trailing comma is not permitted.

In columns without ontology the lines containing labels and IRIs are empty.

Similarly, columns without units (with or without ontology entry) have empty units line.

.. versionadded:: v2
   The optional description of the file.

Example:
    Here is an example with five columns:

    - an index with no units or ontology label
    - the entity spontaneous magnetization with an entry in the ontology
    - a made-up quantity alpha with a unit but no ontology label
    - demagnetizing factor with an ontology entry but no unit
    - a column `description` containing a string description without units or ontology
      label

    The file has a description reading "Test data".

    To keep this example short the actual IRIs are omitted.

    .. code-block:: text

      #mammos csv v2
      #----------------------------------------------
      # Test data
      #----------------------------------------------
      #,SpontaneousMagnetization,,DemagnetizingFactor,description
      #,https://w3id.org/emm/...,,https://w3id.org/emmo/...,
      #,kA/m,s^2,,
      index,Ms,alpha,DemagnetizingFactor,
      0,1e2,1.2,1,Description of the first data row
      1,1e2,3.4,0.5,Description of the second data row
      2,1e2,5.6,0.5,Description of the third data row

"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import mammos_units as u
import pandas as pd

import mammos_entity as me

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing

    import mammos_entity


def entities_to_file(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> None:
    """Write entity data to file.

    Supported file formats:

    - csv

    The file format is inferred from the filename suffix.

    The file structure is explained in the module-level documentation.

    The arguments `_filename` and `_description` are named in such a way that an user
    could define entities named `filename` and `description`. They are furthermore
    defined as positional arguments.

    Args:
        _filename: Name or path of file where to store data.
        _description: Optional description of data. If given, it wil appear
            commented in the metadata lines.
        **entities: Data to be saved to file.

    """
    if not entities:
        raise RuntimeError("No data to write.")
    _entities_to_csv(_filename, _description, **entities)


def entities_to_csv(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> None:
    """Write tabular data to csv file."""
    if not entities:
        raise RuntimeError("No data to write.")
    warnings.warn(
        "Use `entities_to_file`, the file type is inferred from the file extension.",
        DeprecationWarning,
        stacklevel=2,
    )
    _entities_to_csv(_filename, _description, **entities)


def _entities_to_csv(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> None:
    ontology_labels = []
    ontology_iris = []
    units = []
    data = {}
    if_scalar_list = []
    for name, element in entities.items():
        if isinstance(element, me.Entity):
            ontology_labels.append(element.ontology_label)
            ontology_iris.append(element.ontology.iri)
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        elif isinstance(element, u.Quantity):
            ontology_labels.append("")
            ontology_iris.append("")
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        else:
            ontology_labels.append("")
            ontology_iris.append("")
            units.append("")
            data[name] = element
            if_scalar_list.append(pd.api.types.is_scalar(element))

    dataframe = (
        pd.DataFrame(data, index=[0]) if all(if_scalar_list) else pd.DataFrame(data)
    )
    with open(_filename, "w", newline="") as f:
        # newline="" required for pandas to_csv
        f.write(f"#mammos csv v2{os.linesep}")
        if _description:
            f.write("#" + "-" * 40 + os.linesep)
            for d in _description.split("\n"):
                f.write(f"# {d}{os.linesep}")
            f.write("#" + "-" * 40 + os.linesep)
        f.write("#" + ",".join(ontology_labels) + os.linesep)
        f.write("#" + ",".join(ontology_iris) + os.linesep)
        f.write("#" + ",".join(units) + os.linesep)
        dataframe.to_csv(f, index=False)


class EntityCollection:
    """Container class storing entity-like objects."""

    def __init__(self, **kwargs):
        """Initialize EntityCollection, keywords become attributes of the class."""
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        """Show container elements."""
        args = "\n".join(f"    {key}={val!r}," for key, val in self.__dict__.items())
        return f"{self.__class__.__name__}(\n{args}\n)"

    def to_dataframe(self, include_units: bool = True):
        """Convert values to dataframe."""

        def unit(key: str) -> str:
            """Get unit for element key.

            Returns:
                A string " (unit)" if the element has a unit, otherwise an empty string.
            """
            unit = getattr(getattr(self, key), "unit", None)
            if unit and str(unit):
                return f" ({unit!s})"
            else:
                return ""

        return pd.DataFrame(
            {
                f"{key}{unit(key) if include_units else ''}": getattr(val, "value", val)
                for key, val in self.__dict__.items()
            }
        )


def entities_from_file(filename: str | Path) -> EntityCollection:
    """Read files with ontology metadata.

    Reads a file as defined in the module description. The returned container provides
    access to the individual columns.
    """
    return _entities_from_csv(filename)


def entities_from_csv(filename: str | Path) -> EntityCollection:
    """Read CSV file with ontology metadata."""
    warnings.warn(
        "Use `entities_from_file`, the file type is inferred from the file extension.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _entities_from_csv(filename)


def _entities_from_csv(filename: str | Path) -> EntityCollection:
    with open(filename) as f:
        file_version_information = f.readline()
        version = re.search(r"v\d+", file_version_information)
        if not version:
            raise RuntimeError("File does not have version information in line 1.")
        if version.group() not in ["v1", "v2"]:
            raise RuntimeError(
                f"Reading mammos csv {version.group()} is not supported."
            )
        next_line = f.readline()
        if "#--" in next_line:
            while True:
                if "#--" in f.readline():
                    break
            next_line = f.readline()
        ontology_labels = next_line.strip().removeprefix("#").split(",")
        _ontology_iris = f.readline().strip().removeprefix("#").split(",")
        units = f.readline().strip().removeprefix("#").split(",")
        names = f.readline().strip().removeprefix("#").split(",")

        f.seek(0)
        data = pd.read_csv(f, comment="#", sep=",")
        scalar_data = len(data) == 1

    result = EntityCollection()

    for name, ontology_label, unit in zip(names, ontology_labels, units, strict=False):
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            setattr(result, name, me.Entity(ontology_label, data_values, unit))
        elif unit:
            setattr(result, name, u.Quantity(data_values, unit))
        else:
            setattr(result, name, data_values)

    return result
