"""EntityCollection class."""

import copy
import textwrap

import pandas as pd


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
        self._entities = kwargs

    @property
    def entities(self) -> dict:
        """Dictionary of entities stored in the collection."""
        return self._entities

    def __setattr__(self, name, value):
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
            self._entities[name] = value

    def __getattr__(self, name):
        """Access entities via dot notation.

        Allow access to entities using ``collection.name`` as a short-hand for
        ``collection.entities["name"]``.

        If a property/method with the same name exists it gets precedence. In such cases
        access to the entity is only possible via the ``entities`` dictionary.
        """
        try:
            return self._entities[name]
        except KeyError:
            raise AttributeError(name) from None

    def __delattr__(self, name):
        """Delete element from collection.

        If an entity with ``name`` is in the collections internal dictionary
        (``entities``) it is removed from that dictionary. If a method with the same
        name exists, it gets precedence. In such cases delete from the ``entities``
        dictionary directly by using ``del collection.entities[name]``.
        """
        if name.startswith("_") or hasattr(self.__class__, name):
            object.__delattr__(self, name)
        elif name in self.entities:
            del self.entities[name]
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

    def __copy__(self):
        """Shallow copy of entities."""
        return self.__class__(description=self.description, **self.entities)

    def __deepcopy__(self, memo):
        """Deep copy of entities."""
        entities = {
            name: copy.deepcopy(entity, memo) for name, entity in self.entities.items()
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

    def __repr__(self):
        """Show container elements."""
        args = f"description={self.description!r},\n"
        args += "\n".join(f"{key}={val!r}," for key, val in self.entities.items())
        return f"{self.__class__.__name__}(\n{textwrap.indent(args, ' ' * 4)}\n)"

    def to_dataframe(self, include_units: bool = False):
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
                for key, val in self.entities.items()
            }
        )
