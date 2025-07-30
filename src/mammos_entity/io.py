r"""Support for reading and writing Entity files.

:py:mod:`mammos_entity.io` can write and read data in CSV and YAML format.

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

    >>> from pathlib import Path
    >>> import mammos_entity as me
    >>> import mammos_units as u
    >>> me.io.entities_to_file(
    ...     "example.csv",
    ...     "Test data",
    ...     index=[0, 1, 2],
    ...     Ms=me.Ms([1e2, 1e2, 1e2], "kA/m"),
    ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
    ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
    ...     description=[
    ...         "Description of the first data row",
    ...         "Description of the second data row",
    ...         "Description of the third data row",
    ...     ],
    ... )

    The new file has the following content:

    >>> print(Path("example.csv").read_text())
    #mammos csv v2
    #----------------------------------------
    # Test data
    #----------------------------------------
    #,SpontaneousMagnetization,,DemagnetizingFactor,
    #,https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,,https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
    #,kA / m,s2,,
    index,Ms,alpha,DemagnetizingFactor,description
    0,100.0,1.2,1.0,Description of the first data row
    1,100.0,3.4,0.5,Description of the second data row
    2,100.0,5.6,0.5,Description of the third data row
    <BLANKLINE>

    Finally, remove the file.

    >>> Path("example.csv").unlink()

YAML
====

YAML files written by :py:mod:`mammos_entity.io` have the following format:

- They have two top-level keys ``metadata`` and ``data``.
- ``metadata`` contains keys

  - ``version``: a string that matches the regex v\\d+
  - ``description``: a (multi-line) string with arbitrary content

- ``data`` contains on key per object saved in the file. Each object has the keys:

  - ``ontology_label``: label in the ontology, ``null`` if the element is no Entity.
  - ``ontology_iri``: IRI of the entity, ``null`` if the element is no Entity.
  - ``unit``: unit of the entity or quantity, ``null`` if the element has no unit, empty
    string for dimensionless quantities and entities.
  - ``value``: value of the data.


Example:
    Here is an example with six entries:

    - an index with no units or ontology label
    - the entity spontaneous magnetization with an entry in the ontology
    - a made-up quantity alpha with a unit but no ontology label
    - demagnetizing factor with an ontology entry but no unit
    - a column `description` containing a string description without units or ontology
      label
    - an element Tc with only a single value

    The file has a description reading "Test data".

    >>> from pathlib import Path
    >>> import mammos_entity as me
    >>> import mammos_units as u
    >>> me.io.entities_to_file(
    ...     "example.yaml",
    ...     "Test data",
    ...     index=[0, 1, 2],
    ...     Ms=me.Ms([1e2, 1e2, 1e2], "kA/m"),
    ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
    ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
    ...     description=[
    ...         "Description of the first data row",
    ...         "Description of the second data row",
    ...         "Description of the third data row",
    ...     ],
    ...     Tc=me.Tc(300, "K"),
    ... )

    The new file has the following content:

    >>> print(Path("example.yaml").read_text())
    metadata:
      version: v1
      description: Test data
    data:
      index:
        ontology_label: null
        ontology_iri: null
        unit: null
        value: [0, 1, 2]
      Ms:
        ontology_label: SpontaneousMagnetization
        ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
        unit: kA / m
        value: [100.0, 100.0, 100.0]
      alpha:
        ontology_label: null
        ontology_iri: null
        unit: s2
        value: [1.2, 3.4, 5.6]
      DemagnetizingFactor:
        ontology_label: DemagnetizingFactor
        ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
        unit: ''
        value: [1.0, 0.5, 0.5]
      description:
        ontology_label: null
        ontology_iri: null
        unit: null
        value: [Description of the first data row, Description of the second data row,
          Description of the third data row]
      Tc:
        ontology_label: CurieTemperature
        ontology_iri: https://w3id.org/emmo#EMMO_6b5af5a8_a2d8_4353_a1d6_54c9f778343d
        unit: K
        value: 300.0
    <BLANKLINE>

    Finally, remove the file.

    >>> Path("example.yaml").unlink()

"""  # noqa: E501

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
import pandas as pd
import yaml

import mammos_entity as me

if TYPE_CHECKING:
    from collections.abc import Iterator

    import astropy.units
    import numpy.typing

    import mammos_entity


def entities_to_file(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
) -> None:
    """Write entity data to file.

    Supported file formats:

    - CSV
    - YAML

    The file format is inferred from the filename suffix:

    - ``.csv`` is written as CSV
    - ``.yaml`` and ``.yml`` are written as YAML

    The file structure is explained in the module-level documentation.

    The arguments `_filename` and `_description` are named in such a way that an user
    could define entities named `filename` and `description`. They are furthermore
    defined as positional only arguments.

    Args:
        _filename: Name or path of file where to store data.
        _description: Optional description of data. If given, it will appear in the
            metadata part of the file.
        **entities: Data to be saved to file. For CSV all entity like objects need to
            have the same length and shape 0 or 1, YAML supports different lengths and
            arbitrary shape.

    """
    if not entities:
        raise RuntimeError("No data to write.")
    match Path(_filename).suffix:
        case ".csv":
            _entities_to_csv(_filename, _description, **entities)
        case ".yml" | ".yaml":
            _entities_to_yaml(_filename, _description, **entities)
        case unknown_suffix:
            raise ValueError(f"File type '{unknown_suffix}' not supported.")


def entities_to_csv(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
) -> None:
    """Deprecated: write tabular data to csv file, use entities_to_file."""
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
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
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

    if any(if_scalar_list) and not all(if_scalar_list):
        raise ValueError("All entities must have the same shape, either 0 or 1.")

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


def _entities_to_yaml(
    _filename: str | Path,
    _description: str | None = None,
    /,
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
) -> None:
    def _preprocess_entity_args(entities: dict[str, str]) -> Iterator[tuple]:
        """Extract name, label, iri, unit and value for each item."""
        for name, element in entities.items():
            if isinstance(element, me.Entity):
                label = element.ontology_label
                iri = element.ontology.iri
                unit = str(element.unit)
                value = element.value.tolist()
            elif isinstance(element, u.Quantity):
                label = None
                iri = None
                unit = str(element.unit)
                value = element.value.tolist()
            else:
                label = None
                iri = None
                unit = None
                value = np.asanyarray(element).tolist()
            yield name, label, iri, unit, value

    entity_dict = {
        "metadata": {
            "version": "v1",
            "description": _description,
        },
        "data": {
            name: {
                "ontology_label": label,
                "ontology_iri": iri,
                "unit": unit,
                "value": value,
            }
            for name, label, iri, unit, value in _preprocess_entity_args(entities)
        },
    }

    # custom dumper to change style of lists, tuples and multi-line strings
    class _Dumper(yaml.SafeDumper):
        pass

    def _represent_sequence(dumper, value):
        """Display sequence with flow style.

        A list [1, 2, 3] for key `value` is written to file as::

          value: [1, 2, 3]

        instead of::

          value:
            - 1
            - 2
            - 3

        """
        return dumper.represent_sequence(
            "tag:yaml.org,2002:seq", value, flow_style=True
        )

    def _represent_string(dumper, value):
        """Control style of single-line and multi-line strings.

        Single-line strings are written as::

          some_key: Hello

        Multi-line strings are written as::

          some_key: |-
            I am multi-line,
            without a trailing new line.

        """
        style = "|" if "\n" in value else ""
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    _Dumper.add_representer(list, _represent_sequence)
    _Dumper.add_representer(tuple, _represent_sequence)
    _Dumper.add_representer(str, _represent_string)

    with open(_filename, "w") as f:
        yaml.dump(
            entity_dict,
            stream=f,
            Dumper=_Dumper,
            default_flow_style=False,
            sort_keys=False,
        )


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
    access to the individual entities.

    Args:
        filename: Name or path of file to read. The file extension is used to determine
            the file type.

    Returns:
        A container object providing access all entities from the file.
    """
    match Path(filename).suffix:
        case ".csv":
            return _entities_from_csv(filename)
        case ".yml" | ".yaml":
            return _entities_from_yaml(filename)
        case unknown_suffix:
            raise ValueError(f"File type '{unknown_suffix}' not supported.")


def entities_from_csv(filename: str | Path) -> EntityCollection:
    """Deprecated: read CSV file with ontology metadata, use entities_from_file."""
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


def _entities_from_yaml(filename: str | Path) -> EntityCollection:
    with open(filename) as f:
        file_content = yaml.safe_load(f)

    if list(file_content.keys()) != ["metadata", "data"]:
        raise RuntimeError(
            "YAML files must have exactly two top-level keys, 'metadata' and 'data'."
        )

    if "version" not in file_content["metadata"]:
        raise RuntimeError("File does not have a key metadata:version.")

    if (version := file_content["metadata"]["version"]) != "v1":
        raise RuntimeError(f"Reading mammos yaml {version} is not supported.")

    result = EntityCollection()

    for key, item in file_content["data"].items():
        if item["ontology_label"] is not None:
            setattr(
                result,
                key,
                me.Entity(
                    ontology_label=item["ontology_label"],
                    value=item["value"],
                    unit=item["unit"],
                ),
            )
        elif item["unit"] is not None:
            setattr(result, key, u.Quantity(item["value"], item["unit"]))
        else:
            setattr(result, key, item["value"])

    return result


# hide deprecated functions in documentation
__all__ = ["entities_to_file", "entities_from_file", "EntityCollection"]
