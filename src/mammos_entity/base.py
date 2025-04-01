import mammos_units as u
from owlready2.entity import ThingClass

from mammos_entity.onto import mammos_ontology


def si_unit_from_list(list_cls):
    si_unit_cls = [
        cls
        for cls in list_cls
        if mammos_ontology.SICoherentDerivedUnit in cls.ancestors()
    ]
    if not si_unit_cls:
        si_unit_cls = [
            cls
            for cls in list_cls
            if (mammos_ontology.SIDimensionalUnit in cls.ancestors())
        ]
    return si_unit_cls[0].ucumCode[0]


def extract_SI_units(label):
    thing = mammos_ontology.get_by_label(label)
    si_unit = None
    for ancestor in thing.ancestors():
        if hasattr(ancestor, "hasMeasurementUnit") and ancestor.hasMeasurementUnit:
            if sub_class := list(ancestor.hasMeasurementUnit[0].subclasses()):
                si_unit = si_unit_from_list(sub_class)
            elif label := ancestor.hasMeasurementUnit[0].ucumCode:
                si_unit = label[0]
            break
    return si_unit if si_unit != "Cel.K-1" else None


class Entity(u.Quantity):
    """
    An abstract base class representing a scalar physical entity.

    This class serves as a base for entities that have a single numeric value
    with specific physical units.

    :param quantity: The initial quantity with physical units.
    :type quantity: astropy.units.Quantity
    """

    def __new__(cls, label, value, unit=None, **kwargs):
        cls.label = label
        si_unit = extract_SI_units(label)
        if (si_unit is not None) and (unit is not None):
            if not u.Unit(si_unit).is_equivalent(unit):
                raise TypeError(f"The unit {unit} does not match the units of {label}")
        elif (si_unit is not None) and (unit is None):
            unit = si_unit
        elif (si_unit is None) and (unit is not None):
            raise TypeError(
                f"{label} is a unitless entity. Hence, {unit} is inapropriate."
            )
        comp_unit = u.Unit(unit if unit else "").si
        comp_bases = comp_unit.bases
        comp_powers = comp_unit.powers
        return super().__new__(
            cls, value=value, unit=u.CompositeUnit(1, comp_bases, comp_powers), **kwargs
        )

    @property
    def ontology(self) -> ThingClass:
        """
        owlready2.entity.ThingClass: The associated ontology class object.

        Uses the ontology label to fetch the corresponding class from `mammos_ontology`.
        """
        return mammos_ontology.get_by_label(self.label)

    def __repr__(self) -> str:
        """
        Return a string representation of the entity, showing the label,
        numeric value, and unit.

        :return: String representation of the entity.
        :rtype: str
        """
        if self.unit.is_equivalent(u.dimensionless_unscaled):
            repr_str = f"{self.label}(value={self.value})"
        else:
            repr_str = f"{self.label}(value={self.value}, unit={self.unit})"
        return repr_str

    def __str__(self) -> str:
        return self.__repr__()

    def _repr_latex_(self) -> str:
        return self.__repr__()

    @property
    def quantity(self):
        """
        Return a Astropy Quantity representation of this entity.

        This property creates and returns a new `astropy.units.Quantity` object.
        The returned Quantity is a standard Astropy Quantity and does
        not retain any additional metadata or ontology links that may be
        associated with the entity.

        Returns
        -------
        astropy.units.Quantity
            A Quantity object without the ontology.
        """
        return u.Quantity(self.value, self.unit)

    def __array_ufunc__(self, func, method, *inputs, **kwargs):
        """
        Override Astopy's __array_ufunc__ to remove the ontology when
        performing operations and return astropy.units.Quantity.
        """
        result = super().__array_ufunc__(func, method, *inputs, **kwargs)

        if isinstance(result, self.__class__):
            return result.quantity
        else:
            return result
