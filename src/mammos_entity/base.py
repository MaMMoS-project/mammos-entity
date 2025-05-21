"""
Module: base.py

Defines the core `Entity` class, which extends `mammos_units.Quantity` to
link physical quantities to ontology concepts. Also includes helper functions
for inferring the correct SI units from the ontology.
"""

import warnings

import mammos_units as u
from numpy import typing
from owlready2.entity import ThingClass

from mammos_entity.onto import HAVE_INTERNET, mammos_ontology

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


def extract_SI_units(ontology_label: str) -> str | None:
    """
    Given a label for an ontology concept, retrieve the corresponding SI unit
    by traversing the class hierarchy. If a valid unit is found, its UCUM code
    is returned; otherwise, None is returned.

    Parameters
    ----------
    ontology_label : str
        The label of an ontology concept (e.g., 'SpontaneousMagnetization').

    Returns
    -------
    str or None
        The UCUM code of the concept's SI unit, or None if no suitable SI unit
        is found or if the unit is a special case like 'Cel.K-1'.
    """
    thing = mammos_ontology.get_by_label(ontology_label)
    si_unit = None
    for ancestor in thing.ancestors():
        if hasattr(ancestor, "hasMeasurementUnit") and ancestor.hasMeasurementUnit:
            if sub_class := list(ancestor.hasMeasurementUnit[0].subclasses()):
                si_unit = si_unit_from_list(sub_class)
            elif ontology_label := ancestor.hasMeasurementUnit[0].ucumCode:
                si_unit = ontology_label[0]
            break
    # HACK: filter Celsius values as Kelvin and `Cel.K-1` as no units
    if si_unit in {"Cel", "mCel"}:
        si_unit = "K"
    elif si_unit == "Cel.K-1":
        si_unit = None
    return si_unit


class Entity(u.Quantity):
    """
    Represents a physical property or quantity that is linked to an ontology
    concept. Inherits from `mammos_units.Quantity` and enforces unit
    compatibility with the ontology.

    Parameters
    ----------
    ontology_label : str
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
        ontology_label: str,
        value: float | int | typing.ArrayLike = 0,
        unit: str | None = None,
        **kwargs,
    ) -> u.Quantity:
        if HAVE_INTERNET:
            si_unit = extract_SI_units(ontology_label)
            if (si_unit is not None) and (unit is not None):
                if not u.Unit(si_unit).is_equivalent(unit):
                    raise TypeError(
                        f"The unit {unit} does not match the units of {ontology_label}"
                    )
            elif (si_unit is not None) and (unit is None):
                with u.add_enabled_aliases({"Cel": u.K, "mCel": u.K}):
                    comp_si_unit = u.Unit(si_unit).decompose(bases=base_units)
                unit = u.CompositeUnit(1, comp_si_unit.bases, comp_si_unit.powers)
            elif (si_unit is None) and (unit is not None):
                raise TypeError(
                    f"{ontology_label} is a unitless entity."
                    f" Hence, {unit} is inapropriate."
                )
        else:
            warnings.warn(
                message="Failed to load ontology from the interent"
                ". Hence, no check for unit or ontology_label will be performed!",
                category=RuntimeWarning,
                stacklevel=1,
            )
        comp_unit = u.Unit(unit if unit else "")
        out = super().__new__(cls, value=value, unit=comp_unit, **kwargs)
        out._ontology_label = ontology_label
        return out

    @property
    def ontology_label(self) -> str:
        """
        Retrieve the ontology label corresponding to the `ThingClass` that defines the
        given entity in ontology.

        Returns
        -------
        str
            The ontology label corresponding to the right ThingClass.
        """
        return self._ontology_label

    @property
    def ontology(self) -> ThingClass:
        """
        Retrieve the ontology class (ThingClass) corresponding to this Entity's label.

        Returns
        -------
        ThingClass
            The ontology class from `mammos_ontology` that matches the entity's label.
        """
        return mammos_ontology.get_by_label(self.ontology_label)

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

    @property
    def si(self):
        """
        Return the entity in SI units.

        Returns
        -------
        mammos_entity.Entity
            Entity in SI units.
        """
        si_quantity = self.quantity.si
        return self.__class__(
            ontology_label=self.ontology_label,
            value=si_quantity.value,
            unit=si_quantity.unit,
        )

    def to(self, unit: str, equivalencies: list = None, copy: bool = True):
        """
        Override method to convert from one unit to the other. If the coversion requires
        equivalencies, the method returns a `astropy.unit.Quantity` otherwise it returns
        an `Entity` with modified units.

        Parameters
        ----------
        unit : str
            The string defining the target unit to convert to (e.g., 'mJ/m').
        equivalencies : list | optional
            List of equivalencies to be used for unit conversion.
        copy : bool | optional
            If `True` (default), then the value is copied.  Otherwise, a copy
            will only be made if necessary.

        Returns
        -------
        mammos_units.Quantity
            If equivalencies are used to convert the units.
        mammos_entity.Entity
            If equivalencies are not used to convert the units.
        """
        if equivalencies:
            return self.quantity.to(unit=unit, equivalencies=equivalencies, copy=copy)
        else:
            quant = self.quantity.to(unit=unit, copy=copy)
            return self.__class__(
                ontology_label=self.ontology_label, value=quant.value, unit=quant.unit
            )

    def __repr__(self) -> str:
        if self.unit.is_equivalent(u.dimensionless_unscaled):
            repr_str = f"{self.ontology_label}(value={self.value})"
        else:
            repr_str = f"{self.ontology_label}(value={self.value}, unit={self.unit})"
        return repr_str

    def __str__(self) -> str:
        return self.__repr__()

    def _repr_latex_(self) -> str:
        return self.__repr__()

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
