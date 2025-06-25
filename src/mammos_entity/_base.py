"""Define the core `Entity` class.

Defines the core `Entity` class to link physical quantities to ontology concepts. Also
includes helper functions for inferring the correct SI units from the ontology.

"""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING

import mammos_units as u

from mammos_entity._onto import HAVE_INTERNET, mammos_ontology

if TYPE_CHECKING:
    import astropy.units
    import mammos_units
    import numpy.typing
    import owlready2

    import mammos_entity


base_units = [u.T, u.J, u.m, u.A, u.radian, u.kg, u.s, u.K, u.mol, u.cd, u.V]


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

    # Explanation of the following line:
    # 1. We find all ucum (Unified Code for Units of Measure) Code for all units
    #    in si_unit_cls.
    # 2. Astropy complains if it sees unit strings with parentheses, so we exclude
    #    them.
    # 3. We take the first item. It is not important what unit we are selecting
    #    because the ontology does not define a single preferred unit. We are
    #    taking one of the SI coherent derived units or a SI dimensional unit.
    #    astropy will make the conversion to base units later on.
    return [
        unit
        for si_unit_cls_i in si_unit_cls
        for unit in si_unit_cls_i.ucumCode
        if "(" not in unit
    ][0]


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


class Entity:
    """Create a quantity (a value and a unit) linked to the EMMO ontology.

    Represents a physical property or quantity that is linked to an ontology
    concept. It enforces unit compatibility with the ontology.

    Args:
        ontology_label: Ontology label
        value: Value
        unit: Unit

    Examples:
        >>> import mammos_entity as me
        >>> import mammos_units as u
        >>> Ms = me.Entity(ontology_label='SpontaneousMagnetization', value=8e5, unit='A / m')
        >>> H = me.Entity("ExternalMagneticField", 1e4 * u.A / u.m)
        >>> Tc_kK = me.Entity("CurieTemperature", 0.1, unit=u.kK)
        >>> Tc_K = me.Entity("CurieTemperature", Tc_kK, unit=u.K)

    """  # noqa: E501

    def __init__(
        self,
        ontology_label: str,
        value: numpy.typing.ArrayLike
        | mammos_units.Quantity
        | mammos_entity.Entity = 0,
        unit: str | None | mammos_units.UnitBase = None,
    ):
        if isinstance(value, Entity):
            if value.ontology_label != ontology_label:
                raise ValueError(
                    "Incompatible label for initialization."
                    f" Trying to initialize a {ontology_label}"
                    f" with a {value.ontology_label}."
                )
            value = value.quantity
        if unit is None and isinstance(value, u.Quantity):
            unit = value.unit
        if HAVE_INTERNET:
            si_unit = extract_SI_units(ontology_label)
            if (si_unit is not None) and (unit is not None):
                # Remove any set equivalency to enforce unit strictness
                with u.set_enabled_equivalencies(None):
                    are_equivalent = u.Unit(si_unit).is_equivalent(unit)
                if not are_equivalent:
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
                    f" Hence, {unit} is inappropriate."
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
        with u.set_enabled_equivalencies(None):
            self._quantity = u.Quantity(value=value, unit=comp_unit)
        self._ontology_label = ontology_label

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
        return f"{self.ontology_label} {self.ontology.iri}"

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
        return self._quantity

    @property
    def q(self) -> mammos_units.Quantity:
        """Quantity attribute, shorthand for `.quantity`."""
        return self.quantity

    @property
    def value(self) -> numpy.scalar | numpy.ndarray:
        """Numerical data of the entity."""
        return self._quantity.value

    @property
    def unit(self) -> astropy.units.UnitBase:
        """Unit of the entity data."""
        return self._quantity.unit

    @property
    def axis_label(self) -> str:
        """Return an ontology-based axis label for the plots.

        The axis label consist of ontology label and unit:
        - The ontology label is split with spaces at all capital letters
        - The units are added in parentheses.

        Returns:
            A string for labelling the axis corresponding to the entity on a plot.

        Examples:
            >>> import mammos_entity as me
            >>> me.Entity("SpontaneousMagnetization").axis_label
            'Spontaneous Magnetization (A / m)'
            >>> me.Entity("DemagnetizingFactor").axis_label
            'Demagnetizing Factor'
        """
        return re.sub(r"(?<!^)(?=[A-Z])", " ", f"{self.ontology_label}") + (
            f" ({self.unit})" if str(self.unit) else ""
        )

    def __eq__(self, other: mammos_entity.Entity) -> bool:
        """Check if to Entities are identical.

        Entities are considered identical if they have the same ontology label and
        numerical data, i.e. unit prefixes have no effect.

        Examples:
            >>> import mammos_entity as me
            >>> ms_1 = me.Ms(1, "kA/m")
            >>> ms_2 = me.Ms(1e3, "A/m")
            >>> ms_1 == ms_2
            True
            >>> t = me.T(1, "K")
            >>> ms_1 == t
            False
        """
        if not isinstance(other, Entity):
            raise NotImplementedError(
                "Equivalence between mammos_entity.Entity and "
                f"{type(other)} is not defined."
            )
        return (
            self.ontology_label == other.ontology_label
            and self.q.ndim == other.q.ndim
            and u.allclose(self.q, other.q)
        )

    def __repr__(self) -> str:
        args = [f"ontology_label='{self._ontology_label}'", f"value={self.value!r}"]
        if str(self.unit):
            args.append(f"unit='{self.unit!s}'")

        return f"{self.__class__.__name__}({', '.join(args)})"

    def __str__(self) -> str:
        new_line = "\n" if self.value.size > 4 else ""
        if self.unit.is_equivalent(u.dimensionless_unscaled):
            repr_str = f"{self.ontology_label}(value={new_line}{self.value})"
        else:
            repr_str = (
                f"{self.ontology_label}(value={new_line}{self.value}"
                f",{new_line} unit={self.unit})"
            )
        return repr_str

    def _repr_html_(self) -> str:
        html_str = str(self).replace("\n", "<br>").replace(" ", "&nbsp;")
        return f"<samp>{html_str}</samp>"
