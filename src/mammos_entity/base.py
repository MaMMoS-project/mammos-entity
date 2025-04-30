"""
Module: base.py

Defines the core `Entity` class, which extends `mammos_units.Quantity` to
link physical quantities to ontology concepts. Also includes helper functions
for inferring the correct SI units from the ontology.
"""

import mammos_units as u
from numpy import typing
from owlready2.entity import ThingClass

from mammos_entity.onto import mammos_ontology

base_units = [u.J, u.m, u.A, u.T, u.radian, u.kg, u.s, u.K]


def si_unit_from_list(list_cls: list[ThingClass]) -> str:
    """
    Given a list of ontology classes, determine which class corresponds to
    a coherent SI derived unit (or if none found, an SI dimensional unit),
    then return that class's UCUM code.

    Parameters
    ----------
    list_cls : list[ThingClass]
        A list of ontology classes.

    Returns
    -------
    str
        The UCUM code (e.g., "J/m^3", "A/m") for the first identified SI unit
        in the given list of classes.
    """
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


def extract_SI_units(label: str) -> str | None:
    """
    Given a label for an ontology concept, retrieve the corresponding SI unit
    by traversing the class hierarchy. If a valid unit is found, its UCUM code
    is returned; otherwise, None is returned.

    Parameters
    ----------
    label : str
        The label of an ontology concept (e.g., 'SpontaneousMagnetization').

    Returns
    -------
    str or None
        The UCUM code of the concept's SI unit, or None if no suitable SI unit
        is found or if the unit is a special case like 'Cel.K-1'.
    """
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
    Represents a physical property or quantity that is linked to an ontology
    concept. Inherits from `mammos_units.Quantity` and enforces unit
    compatibility with the ontology.

    Parameters
    ----------
    label : str
        The label of an ontology concept (e.g., 'SpontaneousMagnetization').
    value : float | int | typing.ArrayLike
        The numeric value of the physical quantity.
    unit : optional
        The unit of measure for the value (e.g., 'A/m', 'J/m^3'). If omitted,
        the SI unit from the ontology is used (if defined). If the ontology
        indicates no unit (dimensionless), an exception is raised if a unit
        is provided.

    Examples
    --------
    >>> import mammos_entity as me
    >>> m = me.Ms(800000, 'A/m')
    >>> m
    SpontaneousMagnetization(value=800000, unit=A/m)
    """

    def __new__(
        cls,
        label: str,
        value: float | int | typing.ArrayLike = 0,
        unit: str | None = None,
        **kwargs,
    ) -> u.Quantity:
        si_unit = extract_SI_units(label)
        if (si_unit is not None) and (unit is not None):
            if not u.Unit(si_unit).is_equivalent(unit):
                raise TypeError(f"The unit {unit} does not match the units of {label}")
        elif (si_unit is not None) and (unit is None):
            with u.add_enabled_aliases({"Cel": u.K, "mCel": u.K}):
                comp_si_unit = u.Unit(si_unit).decompose(bases=base_units)
            unit = u.CompositeUnit(1, comp_si_unit.bases, comp_si_unit.powers)
        elif (si_unit is None) and (unit is not None):
            raise TypeError(
                f"{label} is a unitless entity. Hence, {unit} is inapropriate."
            )
        comp_unit = u.Unit(unit if unit else "")
        return super().__new__(cls, value=value, unit=comp_unit, **kwargs)

    def __init__(self, label: str, *args, **kwargs):
        self.label = label

    @property
    def ontology(self) -> ThingClass:
        """
        Retrieve the ontology class (ThingClass) corresponding to this Entity's label.

        Returns
        -------
        ThingClass
            The ontology class from `mammos_ontology` that matches the entity's label.
        """
        return mammos_ontology.get_by_label(self.label)

    def __repr__(self) -> str:
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
    def quantity(self) -> u.Quantity:
        """
        Return a standalone `mammos_units.Quantity` object with the same value
        and unit, detached from the ontology link.

        Returns
        -------
        mammos_units.Quantity
            A copy of this entity as a pure physical quantity.
        """
        return u.Quantity(self.value, self.unit)

    def __array_ufunc__(self, func, method, *inputs, **kwargs):
        """
        Override NumPy's universal functions to return a regular quantity rather
        than another `Entity` when performing array operations (e.g., add, multiply)
        since these oprations change the units.
        """
        result = super().__array_ufunc__(func, method, *inputs, **kwargs)

        if isinstance(result, self.__class__):
            return result.quantity
        else:
            return result
