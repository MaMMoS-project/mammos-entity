"""Plotting module."""

from __future__ import annotations

import copy
from contextlib import ContextDecorator
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
from matplotlib.units import AxisInfo, ConversionInterface, registry

from mammos_entity._entity import Entity

if TYPE_CHECKING:
    import astropy.units
    import matplotlib.axis
    import numpy.typing


# inspirations:
# https://numpy.org/doc/stable/user/basics.subclassing.html
# https://docs.astropy.org/en/stable/_modules/astropy/units/quantity.html#Quantity
class _EntityArray(np.ndarray):
    """Entity-enriched Array.

    This class derived from :py:func:`numpy.ndarray` contains entity-related information, such as
    `ontology_label` and `unit`.
    """

    def __new__(
        cls, value: np.typing.ArrayLike, ontology_label: str, unit: astropy.units.Unit | None = None
    ) -> _EntityArray:
        """Create new `_`EntityArray``.

        Args:
            ontology_label: Label defining the entity in the domain ontology MagMO.
            value: Array expressing the numerical value of the entity.
            unit: Astropy unit of the entity.

        Returns:
            Initialized `_EntityArray`.

        """
        obj = np.asarray(value).view(cls)  # cast into `_EntityArray` class
        obj.ontology_label = ontology_label
        obj.unit = unit
        return obj

    def __copy__(self) -> _EntityArray:
        return _EntityArray(copy.copy(self.base), ontology_label=self.ontology_label, unit=self.unit)

    def __array_finalize__(self, obj: numpy.typing.ArrayLike) -> None:
        """Complete class instance if initialized in alternative ways.

        Args:
            obj: Object to be transformed into an `_EntityArray`. Depending on the initialization it might be missing
                the `ontology_label` and `unit` attributes.
        """
        if obj is None:
            return
        self.ontology_label = getattr(obj, "ontology_label", None)
        self.unit = getattr(obj, "unit", None)

    def __str__(self) -> str:
        return f"{self.ontology_label}({self.base}, '{self.unit}')"

    def __repr__(self) -> str:
        return f"_EntityArray({self.ontology_label}, {self.base}, {self.unit})"

    def __getitem__(self, key: int | slice | list[int] | list[bool] | numpy.typing.ArrayLike) -> _EntityArray:
        return _EntityArray(self.base[key], ontology_label=self.ontology_label, unit=self.unit)


# inspiration:
# https://docs.astropy.org/en/stable/_modules/astropy/visualization/units.html
class EntityLikeConverter(ConversionInterface, ContextDecorator):
    """Matplotlib converter for all entity-like objects.

    This converter covers :py:class:`mammos_entity.Entity` and :py:class:`mammos_units.Quantity` objects.
    Simple arrays are covered by default from ``matplotlib`` and they do not require a unit converter.
    """

    def __init__(self):
        """Initialize entity-like converter.

        In this converter the :py:class:`mammos_entity.Entity` class is provided with an ``__array__`` method in order
        to be plotted with :py:mod:`matplotlib` with unit support. Calling ``Entity.__array__`` will generate an
        ``_EntityArray`` object (subclassed from `numpy.ndarray`) containing necessary information to plot an entity.

        The same converter is defined for :py:class:`mammos_entity.Entity` and :py:class:`mammos_units.Quantity` so
        they can be plotted in the same figure.
        """

        def get_entity_array(self, *args, **kwargs) -> _EntityArray:
            """Define an `_EntityArray` from an `Entity` object.

            Args:
                self: Entity to be converted.
                args: extra positional arguments passed to the `_EntityArray` creation.
                kwargs: extra keyword arguments passed to the `_EntityArray` creation.

            Returns:
                Array with entity information.
            """
            return _EntityArray(self.value, self.ontology_label, *args, unit=self.unit, **kwargs)

        Entity.__array__ = get_entity_array

        registry[u.Quantity] = self
        registry[_EntityArray] = self

    @staticmethod
    def axisinfo(unit: tuple[str, astropy.units.Unit], axis: matplotlib.axis.Axis) -> AxisInfo:
        """Define axis information.

        Axis is in the shape ``entity_label (physical_unit)``. If the physical unit is equivalent to dimensionless,
        it will not appear in the axis. If the object is a :py:class:`mammos_units.Quantity`, it will have no
        entity label.

        Args:
            unit: tuple of `(ontology_label, physical_unit)` to describe the Entity-like to be plotted. If the object
                to plot is a :py:class:`mammos_units.Quantity`, the `ontology_label` will be an empty string.
            axis: X or Y axis. In this implementation this parameter is ignored.

        Returns:
            Axis information with label including ontology label and physical unit if available.
        """
        label = unit[0]
        if not unit[1].is_equivalent(""):
            # if the physical unit is equivalent dimensionless
            if label:
                label += " "  # add space if label and units are both nonempty
            label += f"({unit[1].to_string('latex_inline')})"
        return AxisInfo(label=label)

    @staticmethod
    def convert(
        x: numpy.typing.ArrayLike, unit: tuple[str, astropy.units.Unit], axis: matplotlib.axis.Axis
    ) -> numpy.typing.ArrayLike:
        """Define conversion.

        This function is called when an object of nonstandard type is added to an axis containing already an object.
        The object is converted to the given `unit`.

        Args:
            x: array to be converted to the correct unit.
            unit: tuple `(ontology_label, physical_unit)` for conversion. If `x.ontology_label` of the given `x` is
                different than the one defined in the `unit` argument,
                `ontology_label`, the conversion fails. If the
            axis: ...

        """
        # TODO: finish docstring
        if unit[0] and getattr(x, "ontology_label", False) and x.ontology_label != unit[0]:
            # `ontology_label` is defined in the axis and `x` is an Entity of different label
            raise RuntimeError(
                f"Incompatible entity labels. Axis is defined with ontology label {unit[0]} and given argument {x} "
                f"is an Entity with ontology_label {x.ontology_label}."
            )  # TODO: test this error
        # TODO: add raises to docstring

        if not x.unit.is_equivalent(unit[1]):
            raise RuntimeError(
                f"Unit conversion error in plotting. Unit {x.unit} of input "
                f"{x} and {unit[1]} of '{unit[0]}' are not equivalent."
            )
        if isinstance(x, u.Quantity):
            q = x
        elif isinstance(x, _EntityArray):
            q = x.base * x.unit
        else:
            raise TypeError(f"Unexpected type '{type(x)}' in conversion of {x}.")
        return q.to_value(unit[1])

    @staticmethod
    def default_units(x, axis) -> tuple[str, astropy.units.Unit]:
        """Define the default plotting unit.

        In this case, the plotting unit is a tuple ``(label, unit)``, where the label is the ontology label of an
        ``Entity``. For a ``Quantity`` the label is an empty string.
        """
        # TODO: finish type hint
        # TODO: docstring
        label = getattr(x, "ontology_label", "")
        physical_unit = u.CompositeUnit(scale=1, bases=x.unit.bases, powers=x.unit.powers)
        return (label, physical_unit)

    def __enter__(self):
        """TODO: add type hint and docstring."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """TODO: add type hint and docstring."""
        Entity.__array__ = None
        del registry[u.Quantity]
        del registry[_EntityArray]


# inspiration:
# https://docs.astropy.org/en/stable/visualization/matplotlib_integration.html
def enable_plotting() -> EntityLikeConverter:
    """Enable plotting of entities as NumPy arrays.

    If used in a ``with`` context it guarantees the changes to be valid only inside of the context.

    Returns:
        # TODO: write returns

    Examples:
        # TODO: write examples

    """
    return EntityLikeConverter()
