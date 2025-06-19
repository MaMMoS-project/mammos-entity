"""Define the core `Entity` class.

Defines the core `Entity` class, which extends `mammos_units.Quantity` to
link physical quantities to ontology concepts. Also includes helper functions
for inferring the correct SI units from the ontology.
"""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np

from mammos_entity._onto import HAVE_INTERNET, mammos_ontology

if TYPE_CHECKING:
    import astropy.units
    import mammos_units
    import numpy.typing
    import owlready2


base_units = [u.T, u.J, u.m, u.A, u.radian, u.kg, u.s, u.K]


def si_unit_from_list(list_cls: list[owlready2.entity.ThingClass]) -> str:
    """Return an SI unit from a list of entities from the EMMO ontology.

    Given a list of ontology classes, determine which class corresponds to
    a coherent SI derived unit (or if none found, an SI dimensional unit),
    then return that class's UCUM code.

    Args:
        list_cls: A list of ontology classes.

    Returns:
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
    """Find SI unit for the given label from the EMMO ontology.

    Given a label for an ontology concept, retrieve the corresponding SI unit
    by traversing the class hierarchy. If a valid unit is found, its UCUM code
    is returned; otherwise, None is returned.

    Args:
        ontology_label: The label of an ontology concept
            (e.g., 'SpontaneousMagnetization').

    Returns:
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
    """Create a quantity (a value and a unit) linked to the EMMO ontology.

    Represents a physical property or quantity that is linked to an ontology
    concept. Inherits from `mammos_units.Quantity` and enforces unit
    compatibility with the ontology.

    Args:
        ontology_label: Ontology label
        value: Value
        unit: Unit

    Examples:
        >>> import mammos_entity as me
        >>> m = me.Ms(800000, 'A/m')
        >>> m
        SpontaneousMagnetization(value=800000.0, unit=A / m)

    """

    _repr_latex_ = None

    def __new__(
        cls,
        ontology_label: str,
        value: float | int | numpy.typing.ArrayLike = 0,
        unit: str | None | mammos_units.UnitBase = None,
        **kwargs,
    ) -> astropy.units.Quantity:
        print("Entity __new__")
        if HAVE_INTERNET:
            si_unit = extract_SI_units(ontology_label)
            if (si_unit is not None) and (unit is not None):
                if not u.Unit(si_unit).is_equivalent(unit):
                    raise u.UnitConversionError(
                        f"The unit '{unit}' is not equivalent to the unit of"
                        f" {ontology_label} '{u.Unit(si_unit)}'"
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

        # Remove any set equivalency to enforce unit strictness
        with u.set_enabled_equivalencies([]):
            print("Entity __new__: will create out")
            out = super().__new__(cls, value=value, unit=comp_unit, **kwargs)
            print("Entity __new__: have created out")
        out._ontology_label = ontology_label
        print(
            "Entity __new__: have set ontology label to:",
            ontology_label,
            "returning now",
        )
        return out

    def __array_finalize__(self, obj):
        print("Entity __array_finalize__")
        print(f"self: {type(self)}, {self}")
        print(f"obj: {type(obj)}, {obj}")
        super().__array_finalize__(obj)
        print(f"self: {type(self)}, {self}")
        print(f"obj: {type(obj)}, {obj}")
        if hasattr(obj, "ontology_label"):
            print(f"ontology_label: {obj.ontology_label}")
        else:
            print("not ontology label defined")

        if obj is None or obj.__class__ is np.ndarray:
            return

        if not hasattr(obj, "ontology_label"):
            raise RuntimeError(
                f"Trying to cast '{obj!r}' to '{self.__class__}' without specifying "
                "ontology_label. This operation is not supported."
            )

        with u.set_enabled_equivalencies(None):
            if not self.unit.is_equivalent(obj.unit):
                raise RuntimeError(
                    "Attempting to create an entity with incompatible units."
                )

        self._ontology_label = obj.ontology_label

    def __quantity_subclass__(self, unit) -> tuple[astropy.units.Quantity, bool]:
        print("calling __quantity_subclass__")
        print(f"__quantity_subclass__ self: {self}")
        print(f"__quantity_subclass__ unit: {unit}")
        with u.set_enabled_equivalencies(None):
            if self.unit.is_equivalent(unit):
                # old and new units are compatible, keep an entity and allow Entity
                # subclasses (if any)
                return u.Quantity, False  # Entity, True
            else:
                # units are incompatible, force u.Quantity, do not allow subclasses
                # to ensure the resulting object is not an Entity
                return u.Quantity, False

    @property
    def ontology_label(self) -> str:
        """The ontology label that links the entity to the EMMO ontology.

        Retrieve the ontology label corresponding to the `ThingClass` that defines the
        given entity in ontology.

        Returns:
            str: The ontology label corresponding to the right ThingClass.

        """
        return self._ontology_label

    @property
    def ontology_label_with_iri(self) -> str:
        """The ontology label with its IRI. Unique link to EMMO ontology.

        Returns the `self.ontology_label` together with the IRI (a URL that
        points to the definition of this entity.) IRI stands for
        Internationalized Resource Identifier.

        If only the IRI is desired, one can use `self.ontology.iri`.

        Returns:
            str: The ontology label corresponding to the right ThingClass,
                 together with the IRI.

        """
        label_with_iri = self.ontology_label + " " + self.ontology.iri

        return label_with_iri

    # FIX: right not this will fail if no internet!
    @property
    def ontology(self) -> owlready2.entity.ThingClass:
        """Retrieve the ontology class corresponding to the entity's label.

        Returns:
            The ontology class from `mammos_ontology` that matches the entity's label.

        """
        return mammos_ontology.get_by_label(self.ontology_label)

    @property
    def quantity(self) -> astropy.units.Quantity:
        """Return the entity as a `mammos_units.Quantity`.

        Return a stand-alone `mammos_units.Quantity` object with the same value
        and unit, detached from the ontology link.

        Returns:
            A copy of this entity as a pure physical quantity.

        """
        return u.Quantity(self.value, self.unit)

    # @property
    # def si(self) -> mammos_entity.Entity:
    #     """Return the entity in SI units.

    #     Returns:
    #         Entity in SI units.

    #     """
    #     si_quantity = self.quantity.si
    #     return self.__class__(
    #         ontology_label=self.ontology_label,
    #         value=si_quantity.value,
    #         unit=si_quantity.unit,
    #     )

    @property
    def axis_label(self) -> str:
        """Return an ontology based axis label for the plots.

        Returns:
            A string for labelling the axis corresponding to the entity on a plot.

        """
        return (
            re.sub(r"(?<!^)(?=[A-Z])", " ", f"{self.ontology_label}")
            + f" ({self.unit})"
        )

    # def to(self, *args, **kwargs) -> astropy.units.Quantity | mammos_entity.Entity:
    #     """Modify the unit of the entity in accordance to the EMMO ontology.

    #     Override method to convert from one unit to the other. If the coversion requires
    #     equivalencies, the method returns a `astropy.unit.Quantity` otherwise it returns
    #     an `Entity` with modified units.

    #     Args:
    #         unit: The string defining the target unit to convert to (e.g., 'mJ/m').
    #         equivalencies: List of equivalencies to be used for unit conversion.
    #         copy: If `True`, then the value is copied.  Otherwise, a copy will only be
    #             made if necessary.

    #     Returns:
    #         mammos_units.Quantity if equivalencies are used to convert the units,
    #         mammos_entity.Entity if equivalencies are not used to convert the units.

    #     """
    #     quantity = self.quantity.to(*args, **kwargs)
    #     with u.set_enabled_equivalencies(None):
    #         if self.quantity.unit.is_equivalent(quantity.unit):
    #             return self.__class__(
    #                 ontology_label=self.ontology_label,
    #                 value=quantity,
    #                 unit=quantity.unit,
    #             )
    #         else:
    #             return quantity

    # def _new_view(self, obj=None, unit=None, propagate_info=True):
    #     view = super()._new_view(obj, unit, propagate_info)
    #     with u.set_enabled_equivalencies(None):
    #         if self.unit.is_equivalent(view.unit):
    #             view._ontology_label = self.ontology_label
    #         else:
    #             return view.quantity

    # def __getitem__(self, key) -> astropy.units.Quantity | mammos_entity.Entity:
    #     item = super().__getitem__(key)
    #     if item.unit != self.unit:
    #         return item.quantity
    #     item._ontology_label = self.ontology_label
    #     return item

    def __repr__(self) -> str:
        new_line = "\n" if self.value.size > 4 else ""
        if self.unit.is_equivalent(u.dimensionless_unscaled):
            repr_str = f"{self.ontology_label}(value={new_line}{self.value})"
        else:
            repr_str = (
                f"{self.ontology_label}(value={new_line}{self.value}"
                f",{new_line} unit={self.unit})"
            )
        return repr_str

    def __str__(self) -> str:
        return self.__repr__()

    # def __array_ufunc__(self, func, method, *inputs, **kwargs):
    #     """Override NumPy universal functions in case of mathematical operations.

    #     Override NumPy's universal functions to return a regular quantity rather
    #     than another `Entity` when performing array operations (e.g., add, multiply)
    #     since these oprations change the units.
    #     """
    #     result = super().__array_ufunc__(func, method, *inputs, **kwargs)

    #     if isinstance(result, self.__class__):
    #         return result.quantity
    #     else:
    #         return result
