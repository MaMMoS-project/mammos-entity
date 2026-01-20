"""EntityCollection class."""

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
                for key, val in self._elements_dictionary.items()
            }
        )
