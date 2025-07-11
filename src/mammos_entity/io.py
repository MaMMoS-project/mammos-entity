r"""Support for reading and writing Entity files.

Currently only a single file format is supported: a CSV file with additional
commented metadata lines. Comments start with #.

- The first line is commented and contains the file version in the form::

     mammos csv v<VERSION>

  The reading code checks the version number (using regex v\d+) to ensure compatibility.
- The second line is commented and contains the preferred ontology label.
- The third line is commented and contains the ontology IRI.
- The fourth line is commented and contains units.
- The fifth line contains the short labels used to refer to individual columns when
  working with the data, e.g. in a :py:class:`pandas.DataFrame`. Omitting spaces in this
  string is advisable.

  Ideally this string is the short ontology label.
- All remaining lines contain data

Elements in a line are separated by a comma without any surrounding whitespace. A
trailing comma is not permitted.

If a column has no ontology entry lines 1 and 2 are empty for this column.

If a column has no units (with or without ontology entry) line 3 has no entry for this
column.

Here is an example with five columns, an index with no units or ontology label, the
entity spontaneous magnetization with an entry in the ontology, a made-up quantity alpha
with a unit but no ontology label, demagnetizing factor with an ontology entry but no
unit, and a column `description` containing a string description without units or
ontology label. To keep this example short the actual IRIs are omitted::

   #mammos csv v1
   #,SpontaneousMagnetization,,DemagnetizingFactor,description
   #,https://w3id.org/emm/...,,https://w3id.org/emmo/...,
   #,kA/m,s^2,,
   index,Ms,alpha,DemagnetizingFactor,
   0,1e2,1.2,1,Description of the first data row
   1,1e2,3.4,0.5,Description of the second data row
   2,1e2,5.6,0.5,Description of the third data row

"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import mammos_units as u
import pandas as pd

import mammos_entity as me

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing

    import mammos_entity


def entities_to_csv(
    filename: str | Path,
    **entities: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
) -> None:
    """Write tabular data to csv file.

    The file structure is explained in the module-level documentation.

    Column names are keys of the dictionary. If an element is of type
    :py:class:`mammos_entity.Entity` ontology label, IRI and unit are added to the
    header, if an element is of type :py:class:`mammos_units.Quantity` its unit is added
    to the header, otherwise all headers are empty.

    """
    if not entities:
        raise RuntimeError("No data to write.")
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
    with open(filename, "w") as f:
        f.write("#mammos csv v1\n")
        f.write("#" + ",".join(ontology_labels) + "\n")
        f.write("#" + ",".join(ontology_iris) + "\n")
        f.write("#" + ",".join(units) + "\n")
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


def entities_from_csv(filename: str | Path) -> EntityCollection:
    """Read CSV file with ontology metadata.

    Reads a file as defined in the module description. The returned container provides
    access to the individual columns.
    """
    with open(filename) as f:
        file_version_information = f.readline()
        version = re.search(r"v\d+", file_version_information)
        if not version:
            raise RuntimeError("File does not have version information in line 1.")
        if version.group() != "v1":
            raise RuntimeError(
                f"Reading mammos csv {version.group()} is not supported."
            )
        ontology_labels = f.readline().removeprefix("#").removesuffix("\n").split(",")
        _ontology_iris = f.readline().removeprefix("#").removesuffix("\n").split(",")
        units = f.readline().removeprefix("#").removesuffix("\n").split(",")
        names = f.readline().removeprefix("#").removesuffix("\n").split(",")

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
