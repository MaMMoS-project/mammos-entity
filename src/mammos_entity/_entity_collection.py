"""EntityCollection class."""

from __future__ import annotations

import copy
import csv
import os
import textwrap
from typing import TYPE_CHECKING

import h5py
import numpy as np
import pandas as pd
import yaml

import mammos_entity as me

from . import units as u

if TYPE_CHECKING:
    import collections.abc

    import astropy
    import numpy.typing

    import mammos_entity


class EntityCollection:
    """Container class storing entity-like objects.

    An :py:class:`~mammos_entity.EntityCollection` groups entities together. It can
    store :py:class:`~mammos_entity.Entity`, :py:class:`~astropy.units.Quantity` and
    other objects (lists, tuples, arrays, etc.). We refer to all of these as
    `entity-like`.

    Common use cases are reading/writing files and conversion to and from
    :py:class:`pandas.DataFrame`.

    :py:class:`EntityCollection` provides access to entities via both attributes and a
    dictionary-like interface. Access via attribute is only possible if the entity name
    is a valid Python name and no property/method of EntityCollection shadows the
    entity. The dictionary interface does not have these limitations.

    Entities can have arbitrary names, with the exception that ``description`` is not
    allowed. Entities passed as keyword arguments when creating the collection must have
    valid Python names.

    Examples:
        >>> import mammos_entity as me

        When creating a new collection entities can be passed as keyword arguments:

        >>> collection = me.EntityCollection("A description", Ms=me.Ms(), T=me.T())
        >>> collection
        EntityCollection(
            description='A description',
            Ms=Entity(ontology_label='SpontaneousMagnetization', value=np.float64(0.0), unit='A / m'),
            T=Entity(ontology_label='ThermodynamicTemperature', value=np.float64(0.0), unit='K'),
        )

        Entities in the collection can be accessed either via attribute or a
        dictionary-like interface:

        >>> collection.Ms
        Entity(ontology_label='SpontaneousMagnetization', value=np.float64(0.0), unit='A / m')
        >>> collection["T"]
        Entity(ontology_label='ThermodynamicTemperature', value=np.float64(0.0), unit='K')

        Additional elements can be added using both interfaces ("private" elements, i.e.
        entity names starting with an underscore can only be set/retrieved using the
        dictionary-like interface):

        >>> collection.A = [1, 2, 3]
        >>> collection["B"] = me.B([4, 5, 6])

        Checking if an entity name exists in a collection can be done with:

        >>> "B" in collection
        True
        >>> "Js" in collection
        False

        Elements can be removed using:

        >>> del collection.T
        >>> del collection.B

        The collection is iterable, elements are tuples ``(name, entity-like)``:

        >>> list(collection)
        [('Ms', Entity(ontology_label='SpontaneousMagnetization', value=np.float64(0.0), unit='A / m')), ('A', [1, 2, 3])]

    """  # noqa: E501

    def __init__(
        self,
        description: str = "",
        **kwargs: mammos_entity.Entity
        | astropy.units.Quantity
        | numpy.typing.ArrayLike,
    ):
        """Initialize EntityCollection, keywords become attributes of the class.

        Args:
            description: Information string to assign to ``description`` attribute.
            **kwargs : entities to be stored in the collection.
        """
        self.description = description
        self._entities = kwargs

    def __getitem__(
        self, key: str
    ) -> mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike:
        return self._entities[key]

    def __setitem__(
        self,
        key: str,
        value: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
    ):
        if key == "description":
            raise KeyError("'description' is not allowed as entity name.")
        self._entities[key] = value

    def __delitem__(self, key: str) -> None:
        del self._entities[key]

    def __iter__(
        self,
    ) -> collections.abc.Iterator[
        tuple[
            str, mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike
        ]
    ]:
        yield from self._entities.items()

    def __len__(self) -> int:
        return len(self._entities)

    def __contains__(self, key: str) -> bool:
        return key in self._entities

    def __setattr__(
        self,
        name: str,
        value: mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike,
    ) -> None:
        """Add new elements to entities dictionary.

        Public name (no leading underscore) becomes part of the ``entities`` dictionary.
        Private names (at least one leading underscore) are added to the class normally.

        If a property/method with the same name exists it takes precedence and the
        entity will not be added to ``entities``. Instead, the property assignment is
        called/the method is overwritten. In such cases add the entity via the dict
        interface ``collection.entities["name"] = value``.
        """
        if name.startswith("_") or hasattr(self.__class__, name):
            object.__setattr__(self, name, value)
        else:
            self[name] = value

    def __getattr__(
        self, name: str
    ) -> mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike:
        """Access entities via dot notation.

        Allow access to entities using ``collection.name`` as a short-hand for
        ``collection.entities["name"]``.

        If a property/method with the same name exists it gets precedence. In such cases
        access to the entity is only possible via the ``entities`` dictionary.
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __delattr__(self, name: str) -> None:
        """Delete element from collection.

        If an entity with ``name`` is in the collections internal dictionary
        (``entities``) it is removed from that dictionary. If a method with the same
        name exists, it gets precedence. In such cases delete from the ``entities``
        dictionary directly by using ``del collection.entities[name]``.
        """
        if name.startswith("_") or hasattr(self.__class__, name):
            object.__delattr__(self, name)
        elif name in self:
            del self[name]
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

    def __dir__(self) -> list[str]:
        dir = super().__dir__()
        dir.extend(self._entities)
        return sorted(dir)

    def __copy__(self):
        """Shallow copy of entities."""
        return self.__class__(description=self.description, **self._entities)

    def __deepcopy__(self, memo):
        """Deep copy of entities."""
        entities = {
            name: copy.deepcopy(entity, memo) for name, entity in self._entities.items()
        }
        return self.__class__(description=self.description, **entities)

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

    def __repr__(self) -> str:
        """Show container elements."""
        args = f"description={self.description!r},\n"
        args += "\n".join(f"{key}={val!r}," for key, val in self._entities.items())
        return f"{self.__class__.__name__}(\n{textwrap.indent(args, ' ' * 4)}\n)"

    def to_dataframe(self, include_units: bool = False) -> pd.DataFrame:
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
                f"{key}{unit(key) if include_units else ''}": np.atleast_1d(
                    getattr(val, "value", val)
                )
                for key, val in self
            }
        )

    def metadata(self) -> dict[str, str | dict[str, str]]:
        """Get entity metadata as dictionary.

        This method creates a dictionary containing metadata for all entities in the
        collection. Keys are names of the (entities) attributes of the collection,
        values are dictionaries with:
        - keys ``ontology_label``, ``unit`` and ``description`` if the attribute is an
          entity
        - key ``unit`` if the attribute is a quantity
        - an empty dictionary otherwise

        In addition there is one key-value pair ``description`` for the collection
        description.

        Example:
        >>> import mammos_entity as me
        >>> import mammos_units as u
        >>> col = me.EntityCollection("The description", Tc=me.Tc(), x=1 * u.m, a=0)
        >>> col.metadata()
        {'description': 'The description', 'Tc': {'ontology_label': 'CurieTemperature', 'unit': 'K', 'description': ''}, 'x': {'unit': 'm'}, 'a': {}}
        """  # noqa: E501
        result = {"description": self.description}
        for name, entity_like in self._entities.items():
            element = {}
            if isinstance(entity_like, me.Entity):
                element["ontology_label"] = entity_like.ontology_label
                element["unit"] = str(entity_like.unit)
                element["description"] = entity_like.description
            elif isinstance(entity_like, u.Quantity):
                element["unit"] = str(entity_like.unit)
            result[name] = element

        return result

    @classmethod
    def from_dataframe(
        cls, dataframe: pd.DataFrame, metadata: dict[str, dict]
    ) -> mammos_entity.EntityCollection:
        """Create EntityCollection from dataframe and metadata.

        The EntityCollection is created by combining metadata with data from the
        dataframe matching key/column names. The available metadata determines whether
        an element becomes an :py:class:`~mammos_entity.Entity``, a
        :py:class:`mammos_units.Quantity` or a numpy array.

        All column names in the `dataframe` must also exist as keys in `metadata` and
        vice versa.

        In addition `metadata` can have a key ``description`` containing a description
        for the collection.

        Args:
            dataframe: A dataframe containing the values for the individual entities.
            metadata: A dictionary with the structure similar to the one defined in
                :py:func:`~EntityCollection.metadata`. The keys ``unit`` and
                ``description`` for an :py:class`~mammos_entity.Entity` are however
                optional. If not present, default units from the ontology and an empty
                description are used.
        """
        metadata = copy.deepcopy(metadata)  # do not modify the user's metadata dict
        description = metadata.pop("description", "")
        if missing_keys := set(dataframe.columns) - set(metadata):
            raise ValueError(
                f"Entity_Metadata is missing for columns: {', '.join(missing_keys)}"
            )
        if missing_keys := set(metadata) - set(dataframe.columns):
            raise ValueError(
                f"Entity_Metadata is missing for columns: {', '.join(missing_keys)}"
            )

        entities = {}
        for name in metadata:
            value = dataframe[name].to_numpy()
            if len(value) == 1:
                value = value[0]

            if "ontology_label" in metadata[name]:
                elem = me.Entity(
                    ontology_label=metadata[name]["ontology_label"],
                    value=value,
                    unit=metadata[name].get("unit"),
                    description=metadata[name].get("description", ""),
                )
            elif "unit" in metadata[name]:
                elem = u.Quantity(
                    value=value,
                    unit=metadata[name]["unit"],
                )
            else:
                elem = value
            entities[name] = elem

        return cls(description=description, **entities)

    def to_csv(self, filename: str | os.PathLike) -> None:
        r"""Write collection to CSV file.

        CSV files contain data in normal CSV format and additional metadata lines at the
        top of the file. Some of the lines are commented with ``#``. This structure is
        fixed and additional comment lines or inline comments in the data table are not
        allowed.

        The lines are, in order:

        - (commented) the file version in the form ``mammos csv v<VERSION>`` (matching
          regex v\d+)
        - (commented, optional) a description of the file, appearing delimited by
          dashed lines
        - (optional, only for entities) the preferred ontology label
        - (optional, only for entities) a description string
        - (optional, only for entities) the ontology IRI
        - (optional, for entities and quantities) units
        - the short labels used to refer to individual columns when working with the
          data,  e.g. in a :py:class:`pandas.DataFrame` (omitting spaces in this string
          is advisable; ideally this string is the short ontology label)
        - all remaining lines contain data.

        Elements in a line are separated by a comma without any surrounding whitespace.
        A trailing comma is not permitted. Line continuation is OS dependent (\r\n on
        Windows, \n on Unix).

        In columns without ontology the lines containing labels, IRIs, and description
        are empty.

        Similarly, columns without units (with or without ontology entry) have empty
        units line.

        For any column, the description line can be empty. Only entities can store
        descriptions, i.e., if the ontology-related lines are empty, the description
        string will not be read.

        .. version-added:: v2
           The optional description of the file.

        .. version-added:: v3
           Additional description metadata row containing a description for each column.

        .. version-changed:: v3
           Ontology labels, entity descriptions, IRIs, and units are no longer
           commented.

        Args:
            filename: Name of the generated file. An existing file with the same name
                is overwritten without notice.

        Raises:
            RuntimeError: If elements of the collection are of type `EntityCollection`.
                Nested collections are not supported in CSV.
            ValueError: If the entities are not tabular. CSV files can only be written
                for collections in which all entities are either scalar or
                one-dimenisional with the same length.

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
            >>> collection = me.EntityCollection(
            ...     description="Test data",
            ...     index=[0, 1, 2],
            ...     Ms=me.Entity("SpontaneousMagnetization", [1e2, 1e2, 1e2], "kA/m", description="Magnetization at 0 Kelvin"),
            ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
            ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
            ...     comment=[
            ...         "Comment in the first row",
            ...         "Comment in the second row",
            ...         "Comment in the third row",
            ...     ],
            ... )
            >>> collection.to_csv("example.csv")

            The new file has the following content:

            >>> print(Path("example.csv").read_text())
            # mammos csv v3
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

        """  # noqa: E501
        if any(isinstance(element, EntityCollection) for _name, element in self):
            raise RuntimeError("Nested collections cannot be saved to CSV.")

        ontology_labels = []
        descriptions = []
        ontology_iris = []
        units = []
        data = {}
        if_scalar_list = []
        for name, element in self:
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
        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(
                csvfile,
                delimiter=",",
                quoting=csv.QUOTE_MINIMAL,
                lineterminator=os.linesep,
            )
            csvfile.write(f"# mammos csv v3{os.linesep}")
            if self.description:
                csvfile.write("#" + "-" * 40 + os.linesep)
                for line in self.description.split("\n"):
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

    def to_yaml(self, filename: str | os.PathLike) -> None:
        r"""Write collection to YAML file.

        YAML files have the following format:

        - two top-level keys ``metadata`` and ``data``
        - ``metadata`` contains one key:

          - ``version``: a string that matches the regex v\d+

        - ``data`` stores one collection node. Collection nodes are recursive and have:

          - ``description``: a (multi-line) string with arbitrary content
          - zero or more additional keys, each representing either

            - an entity-like entry with keys

              - ``ontology_label``: label in the ontology, ``null`` if the element is
                no Entity
              - ``description``: a description string, ``""`` for entities with no
                description and ``null`` if the element is no Entity
              - ``ontology_iri``: IRI of the entity, ``null`` if the element is no
                Entity
              - ``unit``: unit of the entity or quantity, ``null`` if the element has
                no unit, empty string for dimensionless quantities and entities
              - ``value``: value of the data

            - another collection node (nested EntityCollection)

        .. version-added:: v2

           - The ``description`` key for each entity-like entry.
           - Nested collections are supported.

        .. version-changed:: v2

           - The collection ``description`` is stored in ``data:description``.
           - Nested collections are supported.

        Args:
            filename: Name of the generated file. An existing file with the same name
                is overwritten without notice.

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
            >>> collection = me.EntityCollection(
            ...     description="Test data",
            ...     index=[0, 1, 2],
            ...     Ms=me.Entity("SpontaneousMagnetization", [1e2, 1e2, 1e2], "kA/m", description="Magnetization at 0 Kelvin"),
            ...     alpha=[1.2, 3.4, 5.6] * u.s**2,
            ...     DemagnetizingFactor=me.Entity("DemagnetizingFactor", [1, 0.5, 0.5]),
            ...     comment=[
            ...         "Comment in the first row",
            ...         "Comment in the second row",
            ...         "Comment in the third row",
            ...     ],
            ...     Tc=me.Tc(300, "K"),
            ... )
            >>> collection.to_yaml("example.yaml")

            The new file has the following content:

            >>> print(Path("example.yaml").read_text())
            metadata:
              version: v2
            data:
              description: Test data
              index:
                ontology_label: null
                description: null
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
                description: null
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
                description: null
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

        def _serialize_leaf(element):
            if isinstance(element, me.Entity):
                return {
                    "ontology_label": element.ontology_label,
                    "description": element.description,
                    "ontology_iri": element.ontology.iri,
                    "unit": str(element.unit),
                    "value": element.value.tolist(),
                }
            if isinstance(element, u.Quantity):
                return {
                    "ontology_label": None,
                    "description": None,
                    "ontology_iri": None,
                    "unit": str(element.unit),
                    "value": element.value.tolist(),
                }
            return {
                "ontology_label": None,
                "description": None,
                "ontology_iri": None,
                "unit": None,
                "value": np.asanyarray(element).tolist(),
            }

        def _serialize_collection(collection: EntityCollection) -> dict:
            result = {"description": collection.description}
            for name, element in collection:
                if isinstance(element, EntityCollection):
                    result[name] = _serialize_collection(element)
                else:
                    result[name] = _serialize_leaf(element)
            return result

        entity_dict = {
            "metadata": {"version": "v2"},
            "data": _serialize_collection(self),
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

        with open(filename, "w") as f:
            yaml.dump(
                entity_dict,
                stream=f,
                Dumper=_Dumper,
                default_flow_style=False,
                sort_keys=False,
            )

    def to_hdf5(
        self, base: h5py.File | h5py.Group | str | os.PathLike, name: str | None = None
    ) -> h5py.Group | None:
        """Write a collection to an HDF5 group.

        Entities of the collection become datasets in the group. The collection
        description is added to the group attributes.

        Args:
            base: If it is an open HDF5 file or a group in an HDF5 file, data will be
                added to it as new group. If it is a str or PathLike a new HDF5 file
                with the given name will be created. If a file with that name exists
                already, it will be overwritten without notice.
            name: Name for the newly created group. If an element with that name
                exists already in `base` the function will fail. If `name` is ``None``
                entities of the collection will be added directly to `base` and the
                collection description will be added to `base` attributes.

        Returns:
            If `base` is an open `File` or `Group` the newly created group. If `base` is
            a file name nothing is returned (because the file created internally will be
            closed before the function returns).
        """
        return _to_hdf5(self, base, name)


def _to_hdf5(
    data: mammos_entity.EntityLike | mammos_entity.EntityCollection,
    base: h5py.File | h5py.Group | str | os.PathLike,
    name: str | None,
    record_mammos_entity_version: bool = True,
) -> h5py.Dataset | h5py.Group | None:
    """Internal implementation with additional options required for recursion.

    Args:
        data: <see public method>
        base: <see public method>
        name: <see public method>
        record_mammos_entity_version: add mammos_entity version to group/dataset
            attributes.
    """
    if isinstance(base, str | os.PathLike):
        with h5py.File(base, "w") as f:
            _to_hdf5(data, f, name)
            return

    if isinstance(data, EntityCollection):
        group = base.create_group(name, track_order=True) if name is not None else base
        group.attrs["description"] = data.description
        if record_mammos_entity_version:
            group.attrs["mammos_entity_version"] = me.__version__
        for name, entity_like in data:
            _to_hdf5(entity_like, group, name, record_mammos_entity_version=False)
        return group
    else:
        if name is None:
            raise ValueError("'name' must not be None when 'data' is entity-like.")

        if isinstance(data, me.Entity):
            dset = data._to_hdf5(base, name, record_mammos_entity_version=False)
        elif isinstance(data, u.Quantity):
            dset = base.create_dataset(name, data=data.value)
            dset.attrs["unit"] = str(data.unit)
        else:
            dset = base.create_dataset(name, data=data)

        if record_mammos_entity_version:
            dset.attrs["mammos_entity_version"] = me.__version__
        return dset
