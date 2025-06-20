"""Support for reading and writing Entity files.

Currently only a single file format is supported: a CSV file with additional
commented metadata lines. Comments start with #.

- The first row is commented and contains the preferred ontology label.
- The second row is commented and contains the ontology IRI.
- The third row is commented and contains units.
- The fourth row contains the short labels used to refer to individual columns when
  working with the data, e.g. in a :py:class:`pandas.DataFrame`. Omitting spaces in this
  string is advisable.

  Ideally this string is the short ontology label.
- All remaining rows contain data

If a column has no ontology entry rows 1 and 2 are empty for this column.

If a column has no units (with or without ontology entry) row 3 has no entry for this
column.

Here is an example with four columns, an index with no units or ontology label,
spontaneous magnetization from the ontology, a made-up quantity alpha with a unit but no
ontology, and demagnetizing factor with an ontology entry but no unit. To keep this
example short the actual IRIs are omitted::

   #,SpontaneousMagnetization,,DemagnetizingFactor
   #,https://w3id.org/emm/...,,https://w3id.org/emmo/...
   #,kA/m,s^2,
   index,Ms,alpha,DemagnetizingFactor
   0,1e5,1.2,1
   1,1e5,3.4,0.5
   2,1e5,5.6,0.5

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
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
    for name, element in entities.items():
        if isinstance(element, me.Entity):
            ontology_labels.append(element.ontology_label)
            ontology_iris.append(element.ontology.iri)
            units.append(str(element.unit))
            # Convert data to array to not get an error from pandas if only a single
            # row with no array-like data is present (in which case an index would
            # have to be defined separately).
            data[name] = np.asanyarray(element.value)
        elif isinstance(element, u.Quantity):
            ontology_labels.append("")
            ontology_iris.append("")
            units.append(str(element.unit))
            data[name] = np.asanyarray(element.value)
        else:
            ontology_labels.append("")
            ontology_iris.append("")
            units.append("")
            data[name] = np.asanyarray(element)

    dataframe = pd.DataFrame(data)  # will check that all arrays have equal length

    with open(filename, "w") as f:
        f.write("#" + ",".join(ontology_labels) + "\n")
        f.write("#" + ",".join(ontology_iris) + "\n")
        f.write("#" + ",".join(units) + "\n")
        dataframe.to_csv(f, index=False)


class EntityCollection:
    """Container class storing entity-like objects."""

    def __repr__(self):
        """Show content of container."""
        args = '\n'.join(f"    {key}={val!r}," for key, val in self.__dict__.items())
        return f"{self.__class__.__name__}(\n{args}\n)"

    def to_dataframe(self):
        """Convert values to dataframe."""
        return pd.DataFrame(
            {key: getattr(val, "value", val) for key, val in self.__dict__.items()}
        )


def entities_from_csv(filename: str | Path) -> EntityCollection:
    """Read CSV file with ontology metadata.

    Reads a file as defined in the module description. The returned container provides
    access to the individual columns.
    """
    with open(filename) as f:
        ontology_labels = f.readline().removeprefix("#").removesuffix("\n").split(",")
        _ontology_iris = f.readline().removeprefix("#").removesuffix("\n").split(",")
        units = f.readline().removeprefix("#").removesuffix("\n").split(",")
        names = f.readline().removeprefix("#").removesuffix("\n").split(",")

        f.seek(0)
        data = pd.read_csv(f, comment="#", sep=",")

    result = EntityCollection()

    for name, ontology_label, unit in zip(names, ontology_labels, units, strict=False):
        if ontology_label:
            try:
                setattr(result, name, me.Entity(ontology_label, data[name], unit))
            except TypeError as e:
                if "unitless entity. Hence,  is inappropriate" in str(e):
                    setattr(result, name, me.Entity(ontology_label, data[name]))
                else:
                    raise
        elif unit:
            setattr(result, name, u.Quantity(data[name], unit))
        else:
            setattr(result, name, data[name].to_numpy())

    return result
