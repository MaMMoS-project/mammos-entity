"""Plotting module."""

import mammos_units as u
from matplotlib.pyplot import *  # noqa: F403
from matplotlib.units import AxisInfo, ConversionInterface, registry

from mammos_entity._entity import Entity


class EntityLikeConverter(ConversionInterface):
    """Define interface to plot entity-like objects.

    This converter covers :py:class:`mammos_entity.Entity` and :py:class:`mammos_units.Quantity` objects.
    Simple arrays are covered by default from ``matplotlib`` and they do not require a unit converter.
    """

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
        q = x if isinstance(x, u.Quantity) else x.item().q
        if not q.unit.is_equivalent(unit[1]):
            raise RuntimeError(
                f"Conversion error in plotting. Unit {q.unit} of input "
                f"{x} and {unit[1]} of '{unit[0]}' are not equivalent."
            )
        return q.to_value(unit[1])

    @staticmethod
    def default_units(x, axis):
        """Define the default plotting unit.

        In this case, the plotting unit is a tuple ``(label, unit)``, where the label is the ontology label of an
        ``Entity``. For a ``Quantity`` the label is an empty string.
        """
        if isinstance(x, u.Quantity):
            label = ""
            x_unit = x.unit
        else:
            e = x.item()
            label = e.ontology_label
            x_unit = e.unit
        physical_unit = u.CompositeUnit(scale=1, bases=x_unit.bases, powers=x_unit.powers)
        return (label, physical_unit)


registry[Entity] = EntityLikeConverter()
registry[u.Quantity] = EntityLikeConverter()
