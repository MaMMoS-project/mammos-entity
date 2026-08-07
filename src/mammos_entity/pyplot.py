"""Plotting module."""

import matplotlib.units as units
from astropy.visualization import quantity_support
from matplotlib.pyplot import *  # noqa: F403

from mammos_entity._entity import Entity

quantity_support()


class EntityConverter(units.ConversionInterface):
    """Define interface to plot entities."""

    @staticmethod
    def axisinfo(unit, axis):
        """Define axis information."""
        if unit is not None:
            return units.AxisInfo(label=f"{unit[0]} ({unit[1].to_string('latex_inline')})")
        return None

    @staticmethod
    def convert(value, unit, axis):
        """Define conversion."""
        e = value.item()
        if not e.unit.is_equivalent(unit[1]):
            raise RuntimeError(
                f"Conversion error in plotting. Units {e.unit} of "
                f"'{e.ontology_label}' and {unit[1]} of '{unit[0]}' "
                "are not equivalent."
            )
        return e.q.to_value(unit[1])

    @staticmethod
    def default_units(x, axis):
        """Define the default unit."""
        e = x.item()
        return (e.ontology_label, e.unit)


units.registry[Entity] = EntityConverter()
