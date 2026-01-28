"""EntityCollection class."""

from __future__ import annotations

import copy
import textwrap
from typing import TYPE_CHECKING

import pandas as pd

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
                f"{key}{unit(key) if include_units else ''}": getattr(val, "value", val)
                for key, val in self._entities.items()
            }
        )
