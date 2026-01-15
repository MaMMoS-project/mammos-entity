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
- the preferred ontology label.
- a description string.
- the ontology IRI.
- units.
- The short labels used to refer to individual columns when
  working with the data, e.g. in a :py:class:`pandas.DataFrame`. Omitting spaces in this
  string is advisable.
  Ideally this string is the short ontology label.
- All remaining lines contain data.

Elements in a line are separated by a comma without any surrounding whitespace. A
trailing comma is not permitted.

In columns without ontology the lines containing labels and IRIs are empty.

Similarly, columns without units (with or without ontology entry) have empty units line.

For any column, the description line can be empty. Only entities can store descriptions,
i.e., if the ontology-related lines are empty, the description string will not be read.

.. versionadded:: v2
   The optional description of the file.

.. versionadded:: v3
   Additional description metadata row containing a description for each column.
   Ontology labels, entity descriptions, IRIs, and units are no longer commented.

Example:
    Here is an example with five columns:

    - an index with no units or ontology label
    - the entity spontaneous magnetization with an entry in the ontology and a
      description
    - a made-up quantity alpha with a unit but no ontology label
    - demagnetizing factor with an ontology entry but no unit
    - a column `comment` containing a string comment without units or ontology
      label

    The file has a description reading "Test data".

    >>> from pathlib import Path
    >>> import mammos_entity as me
    >>> import mammos_units as u
    >>> me.io.entities_to_file(
    ...     "example.csv",
    ...     "Test data",
    ...     index=[0, 1, 2],
    ...     Ms=me.Ms([1e2, 1e2, 1e2], "kA/m", description="Magnetization at 0 Kelvin"),
    ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
    ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
    ...     comment=[
    ...         "Comment in the first row",
    ...         "Comment in the second row",
    ...         "Comment in the third row",
    ...     ],
    ... )

    The new file has the following content:

    >>> print(Path("example.csv").read_text())
    #mammos csv v3
    #----------------------------------------
    # Test data
    #----------------------------------------
    ,SpontaneousMagnetization,,DemagnetizingFactor,
    ,Magnetization at 0 Kelvin,,,
    ,https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,,https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
    ,kA / m,s2,,
    index,Ms,alpha,DemagnetizingFactor,comment
    0,100.0,1.2,1.0,Comment in the first row
    1,100.0,3.4,0.5,Comment in the second row
    2,100.0,5.6,0.5,Comment in the third row
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
  - ``description`` a description string, ``""`` if the element is no Entity or has no
    description.
  - ``ontology_iri``: IRI of the entity, ``null`` if the element is no Entity.
  - ``unit``: unit of the entity or quantity, ``null`` if the element has no unit, empty
    string for dimensionless quantities and entities.
  - ``value``: value of the data.

.. versionadded:: v2
   The ``description`` key for each object.

Example:
    Here is an example with six entries:

    - an index with no units or ontology label
    - the entity spontaneous magnetization with an entry in the ontology and a
      description
    - a made-up quantity alpha with a unit but no ontology label
    - demagnetizing factor with an ontology entry but no unit
    - a column `comment` containing a string comment without units or ontology
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
    ...     Ms=me.Ms([1e2, 1e2, 1e2], "kA/m", description="Magnetization at 0 Kelvin"),
    ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
    ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
    ...     comment=[
    ...         "Comment in the first row",
    ...         "Comment in the second row",
    ...         "Comment in the third row",
    ...     ],
    ...     Tc=me.Tc(300, "K"),
    ... )

    The new file has the following content:

    >>> print(Path("example.yaml").read_text())
    metadata:
      version: v2
      description: Test data
    data:
      index:
        ontology_label: null
        description: ''
        ontology_iri: null
        unit: null
        value: [0, 1, 2]
      Ms:
        ontology_label: SpontaneousMagnetization
        description: Magnetization at 0 Kelvin
        ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
        unit: kA / m
        value: [100.0, 100.0, 100.0]
      alpha:
        ontology_label: null
        description: ''
        ontology_iri: null
        unit: s2
        value: [1.2, 3.4, 5.6]
      DemagnetizingFactor:
        ontology_label: DemagnetizingFactor
        description: ''
        ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
        unit: ''
        value: [1.0, 0.5, 0.5]
      comment:
        ontology_label: null
        description: ''
        ontology_iri: null
        unit: null
        value: [Comment in the first row, Comment in the second row, Comment in the third
            row]
      Tc:
        ontology_label: CurieTemperature
        description: ''
        ontology_iri: https://w3id.org/emmo#EMMO_6b5af5a8_a2d8_4353_a1d6_54c9f778343d
        unit: K
        value: 300.0
    <BLANKLINE>

    Finally, remove the file.

    >>> Path("example.yaml").unlink()

"""  # noqa: E501

from __future__ import annotations

import csv
import os
import re
import textwrap
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
    /,
    description: str = "",
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
        description: Optional description of data. It is added to the
           metadata part of the file.
        **entities: Data to be saved to file. For CSV all entity like objects need to
            have the same length and shape 0 or 1, YAML supports different lengths and
            arbitrary shape.

    """
    if not entities:
        raise RuntimeError("No data to write.")
    match Path(_filename).suffix:
        case ".csv":
            _entities_to_csv(_filename, description, **entities)
        case ".yml" | ".yaml":
            _entities_to_yaml(_filename, description, **entities)
        case unknown_suffix:
            raise ValueError(f"File type '{unknown_suffix}' not supported.")


def entities_to_csv(
    _filename: str | Path,
    /,
    description: str = "",
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
    _entities_to_csv(_filename, description, **entities)


def _entities_to_csv(
    _filename: str | Path,
    /,
    description: str = "",
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
) -> None:
    ontology_labels = []
    descriptions = []
    ontology_iris = []
    units = []
    data = {}
    if_scalar_list = []
    for name, element in entities.items():
        if isinstance(element, me.Entity):
            ontology_labels.append(element.ontology_label)
            descriptions.append(element.description)
            ontology_iris.append(element.ontology.iri)
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        elif isinstance(element, u.Quantity):
            ontology_labels.append("")
            descriptions.append("")
            ontology_iris.append("")
            units.append(str(element.unit))
            data[name] = element.value
            if_scalar_list.append(pd.api.types.is_scalar(element.value))
        else:
            ontology_labels.append("")
            descriptions.append("")
            ontology_iris.append("")
            units.append("")
            data[name] = element
            if_scalar_list.append(pd.api.types.is_scalar(element))

    if any(if_scalar_list) and not all(if_scalar_list):
        raise ValueError("All entities must have the same shape, either 0 or 1.")

    dataframe = (
        pd.DataFrame(data, index=[0]) if all(if_scalar_list) else pd.DataFrame(data)
    )
    with open(_filename, "w", newline="") as csvfile:
        writer = csv.writer(
            csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator=os.linesep
        )
        csvfile.write(f"#mammos csv v3{os.linesep}")
        if description:
            csvfile.write("#" + "-" * 40 + os.linesep)
            for line in description.split("\n"):
                csvfile.write(f"# {line}{os.linesep}")
            csvfile.write("#" + "-" * 40 + os.linesep)
        writer.writerows(
            [
                ontology_labels,
                descriptions,
                ontology_iris,
                units,
            ]
        )
        dataframe.to_csv(csvfile, index=False)


def _entities_to_yaml(
    _filename: str | Path,
    /,
    description: str = "",
    **entities: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
) -> None:
    def _preprocess_entity_args(entities: dict[str, str]) -> Iterator[tuple]:
        """Extract name, label, description, iri, unit and value for each item."""
        for name, element in entities.items():
            if isinstance(element, me.Entity):
                label = element.ontology_label
                description = element.description
                iri = element.ontology.iri
                unit = str(element.unit)
                value = element.value.tolist()
            elif isinstance(element, u.Quantity):
                label = None
                description = ""
                iri = None
                unit = str(element.unit)
                value = element.value.tolist()
            else:
                label = None
                description = ""
                iri = None
                unit = None
                value = np.asanyarray(element).tolist()
            yield name, label, description, iri, unit, value

    entity_dict = {
        "metadata": {
            "version": "v2",
            "description": description,
        },
        "data": {
            name: {
                "ontology_label": label,
                "description": descr,
                "ontology_iri": iri,
                "unit": unit,
                "value": value,
            }
            for name, label, descr, iri, unit, value in _preprocess_entity_args(
                entities
            )
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
    """Container class storing entity-like objects.

    Attributes:
        description: String containing information about the ``EntityCollection``.
    """

    def __init__(self, description: str = "", **kwargs):
        """Initialize EntityCollection, keywords become attributes of the class.

        Args:
            description: Information string to assign to ``description`` attribute.
            **kwargs : entities to be stored in the collection.
        """
        self.description = description
        for key, val in kwargs.items():
            setattr(self, key, val)

    @property
    def description(self) -> str:
        """Additional description of the entity collection.

        The description is a string containing any information relevant to the entity
        collection. This can include, e.g., whether it is a set of experimental
        or simulation quantities or outline the overall workflow.
        """
        return self._description

    @description.setter
    def description(self, value) -> None:
        if isinstance(value, str):
            self._description = value
        else:
            raise ValueError(
                f"Description must be a string. "
                f"Received value: {value} of type: {type(value)}."
            )

    @property
    def _elements_dictionary(self):
        """Return a dictionary of all elements stored in the collection."""
        elements = {k: val for k, val in vars(self).items() if k != "_description"}
        return elements

    def __repr__(self):
        """Show container elements."""
        args = f"description={self.description!r},\n"
        args += "\n".join(
            f"{key}={val!r}," for key, val in self._elements_dictionary.items()
        )
        return f"{self.__class__.__name__}(\n{textwrap.indent(args, ' ' * 4)}\n)"

    def to_dataframe(self, include_units: bool = True):
        """Convert values to dataframe.

        Args:
            include_units: If true, include units in the dataframe column names.
        """

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
                for key, val in self._elements_dictionary.items()
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
    with open(filename, newline="") as csvfile:
        file_version_information = csvfile.readline()

        try:
            version = re.search(r"v\d+", file_version_information)
        except StopIteration:
            raise RuntimeError(f"Trying to read empty file: {filename}") from None

        if not version:
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
                    collection_description.append(line.strip().removeprefix("# "))
        else:
            # reset the file position
            csvfile.seek(position)

        # read ontology metadata
        if version_number >= 3:
            reader = csv.reader(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
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

    result = EntityCollection(description="\n".join(collection_description))

    for name, ontology_label, description, iri, unit in zip(
        names, ontology_labels, descriptions, ontology_iris, units, strict=True
    ):
        data_values = data[name].values if not scalar_data else data[name].values[0]
        if ontology_label:
            entity = me.Entity(
                ontology_label=ontology_label,
                value=data_values,
                unit=unit,
                description=description,
            )
            _check_iri(entity, iri)
            setattr(result, name, entity)
        elif unit:
            setattr(result, name, u.Quantity(data_values, unit))
        else:
            setattr(result, name, data_values)

    return result


def _entities_from_yaml(filename: str | Path) -> EntityCollection:
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

    collection_description = file_content["metadata"].get("description", "")
    result = EntityCollection(description=collection_description)

    if not file_content["data"]:
        raise RuntimeError("'data' does not contain anything.")

    if version_number >= 2:
        req_subkeys = {"ontology_label", "description", "ontology_iri", "unit", "value"}
    else:
        req_subkeys = {"ontology_label", "ontology_iri", "unit", "value"}

    for key, item in file_content["data"].items():
        if set(item) != req_subkeys:
            raise RuntimeError(
                f"Element '{key}' does not have the required keys,"
                f" expected {req_subkeys}, found {list(item)}."
            )
        if item["ontology_label"] is not None:
            entity = me.Entity(
                ontology_label=item["ontology_label"],
                value=item["value"],
                unit=item["unit"],
                description=item.get("description", ""),
            )
            _check_iri(entity, item["ontology_iri"])
            setattr(result, key, entity)
        elif item["unit"] is not None:
            setattr(result, key, u.Quantity(item["value"], item["unit"]))
        else:
            setattr(result, key, item["value"])

    return result


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


# hide deprecated functions in documentation
__all__ = ["entities_to_file", "entities_from_file", "EntityCollection"]
