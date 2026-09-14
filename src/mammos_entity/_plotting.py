"""Plotting module."""

from __future__ import annotations

import copy
from contextlib import ContextDecorator

import mammos_units as u
import numpy as np
from matplotlib.units import AxisInfo, ConversionInterface, registry

from mammos_entity._entity import Entity


class _EntityArray(np.ndarray):
    """Entity-enriched Array.

    This class derived from :py:func:`numpy.ndarray` contains entity-related information, such as
    `ontology_label` and `unit`.

    Inspirations: https://numpy.org/doc/stable/user/basics.subclassing.html#slightly-more-realistic-example-attribute-added-to-existing-array
    https://docs.astropy.org/en/stable/_modules/astropy/units/quantity.html#Quantity
    """  # noqa: 501

    def __new__(cls, value, ontology_label: str, unit=None):
        """Create new `_`EntityArray``.

        Args:
            ontology_label: Label defining the entity in the domain ontology MagMO.
            value: Array expressing the numerical value of the entity.
            unit: Astropy unit of the entity.

        """
        obj = np.asarray(value).view(cls)  # cast into `_EntityArray` class
        obj.ontology_label = ontology_label
        obj.unit = unit
        return obj

    def __copy__(self):
        return _EntityArray(copy.copy(self.base), ontology_label=self.ontology_label, unit=self.unit)

    def __array_finalize__(self, obj):
        """Complete class instance if initialized in alternative ways."""
        if obj is None:
            return
        self.ontology_label = getattr(obj, "ontology_label", None)
        self.unit = getattr(obj, "unit", None)

    def __str__(self):
        return f"{self.ontology_label}({self.base}, '{self.unit}')"

    def __repr__(self):
        return f"_EntityArray({self.ontology_label}, {self.base}, {self.unit})"

    def __getitem__(self, key):
        return _EntityArray(self.base[key], ontology_label=self.ontology_label, unit=self.unit)


class EntityLikeConverter(ConversionInterface, ContextDecorator):
    """Matplotlib converter for all entity-like objects.

    This converter covers :py:class:`mammos_entity.Entity` and :py:class:`mammos_units.Quantity` objects.
    Simple arrays are covered by default from ``matplotlib`` and they do not require a unit converter.

    Inspiration: https://docs.astropy.org/en/stable/_modules/astropy/visualization/units.html#quantity_support
    """

    def __init__(self):
        def get_entity_array(self, *args, **kwargs):
            return _EntityArray(self.value, ontology_label=self.ontology_label, unit=self.unit)

        Entity.__array__ = get_entity_array

        # registry[Entity] = self
        registry[u.Quantity] = self
        registry[_EntityArray] = self

    @staticmethod
    def axisinfo(unit, axis):
        """Define axis information.

        Axis is in the shape ``entity_label (physical_unit)``. If the physical unit is equivalent to dimensionless,
        it will not appear in the axis. If the object is a :py:class:`mammos_units.Quantity`, it will have no
        entity label.
        """
        label = unit[0]
        if not unit[1].is_equivalent(""):
            # if the physical unit is equivalent dimensionless
            if label:
                label += " "  # add space if label and units are both nonempty
            label += f"({unit[1].to_string('latex_inline')})"
        return AxisInfo(label=label)

    @staticmethod
    def convert(x, unit, axis):
        """Define conversion."""
        if not x.unit.is_equivalent(unit[1]):
            raise RuntimeError(
                f"Conversion error in plotting. Unit {x.unit} of input "
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
    def default_units(x, axis):
        """Define the default plotting unit.

        In this case, the plotting unit is a tuple ``(label, unit)``, where the label is the ontology label of an
        ``Entity``. For a ``Quantity`` the label is an empty string.
        """
        label = getattr(x, "ontology_label", "")
        physical_unit = u.CompositeUnit(scale=1, bases=x.unit.bases, powers=x.unit.powers)
        return (label, physical_unit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        Entity.__array__ = None
        # del registry[Entity]
        del registry[u.Quantity]
        del registry[_EntityArray]


def enable_plotting():
    """Enable plotting of entities as NumPy arrays.

    This function provides the entities with the ``__array__`` method. This returns an
    :py:func:`mammos_entity.pyplot._EntityArray` object subclassed from :py:func:`numpy.ndarray`,
    endowed with the Entity necessary attributes for plotting.

    Inspiration: https://docs.astropy.org/en/stable/_modules/astropy/visualization/units.html#quantity_support
    """
    return EntityLikeConverter()
