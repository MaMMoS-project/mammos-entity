"""Define the core `Entity` class.

Defines the core `Entity` class to link physical quantities to ontology concepts. Also
includes helper functions for inferring the correct SI units from the ontology.

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import mammos_units as u

import mammos_entity as me
from mammos_entity._ontology import mammos_ontology

if TYPE_CHECKING:
    import astropy.units
    import h5py
    import mammos_units
    import numpy.typing
    import owlready2

    import mammos_entity


base_units = [u.T, u.J, u.m, u.A, u.radian, u.kg, u.s, u.K, u.mol, u.cd, u.V]
mammos_equivalencies = u.temperature()


def _si_unit_from_list(list_cls: list[owlready2.entity.ThingClass]) -> str:
    """Return an SI unit from a list of entities from the EMMO ontology.

    Given a list of ontology classes, determine which class corresponds to
    a coherent SI derived unit (or if none found, an SI dimensional unit),
    then return that class's UCUM code.

    Given a list of ontology classes, we consider only the ones that are classified
    as `SIDimensionalUnit` and we filter out the ones classified as `NonCoherent`.
    If a non `Derived` unit can be found, than we filter out all the `Derived` units.

    Args:
        list_cls: A list of ontology classes.

    Returns:
        The UCUM code (e.g., "J/m^3", "A/m") for the first identified SI unit
        in the given list of classes.

    """
    possible_units = [
        c
        for c in list_cls
        if (
            mammos_ontology.SIDimensionalUnit in c.ancestors()
            and mammos_ontology.SINonCoherentUnit not in c.ancestors()
            and mammos_ontology.SINonCoherentDerivedUnit not in c.ancestors()
        )
    ]
    not_derived = [
        c for c in possible_units if (mammos_ontology.DerivedUnit not in c.ancestors())
    ]
    if not_derived:
        possible_units = not_derived

    # Explanation of the following lines:
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
        for unit_class in possible_units
        for unit in unit_class.ucumCode
        if "(" not in unit
    ][0]


def _extract_SI_units(ontology_label: str) -> str:
    """Find SI unit for the given label from the EMMO ontology.

    Given a label for an ontology concept, retrieve the corresponding SI unit
    by traversing the class hierarchy. If a valid unit is found, its UCUM code
    is returned; otherwise, an empty string is returned (equivalent to dimensionless).

    Args:
        ontology_label: The label of an ontology concept
            (e.g., 'SpontaneousMagnetization').

    Returns:
        The UCUM code of the concept's SI unit, or None if no suitable SI unit
        is found or if the unit is a special case like 'Cel.K-1'.

    """
    thing = mammos_ontology.get_by_label(ontology_label)
    si_unit = ""
    for ancestor in thing.ancestors():
        if hasattr(ancestor, "hasMeasurementUnit") and ancestor.hasMeasurementUnit:
            if ancestor.hasMeasurementUnit[0] == mammos_ontology.get_by_label(
                "DimensionlessUnit"
            ):
                si_unit = ""
            elif sub_class := list(ancestor.hasMeasurementUnit[0].subclasses()):
                si_unit = _si_unit_from_list(sub_class)
            elif ontology_label := ancestor.hasMeasurementUnit[0].ucumCode:
                si_unit = ontology_label[0]
            break
    return si_unit


class Entity:
    """Create a quantity (a value and a unit) linked to the EMMO ontology.

    Represents a physical property or quantity that is linked to an ontology
    concept. It enforces unit compatibility with the ontology.

    Args:
        ontology_label: Ontology label
        value: Value
        unit: Unit
        description: Description

    Examples:
        >>> import mammos_entity as me
        >>> import mammos_units as u
        >>> Ms = me.Entity(ontology_label='SpontaneousMagnetization', value=8e5, unit='A / m')
        >>> H = me.Entity("ExternalMagneticField", 1e4 * u.A / u.m)
        >>> Tc_mK = me.Entity("CurieTemperature", 300, unit=u.mK)
        >>> Tc_K = me.Entity("CurieTemperature", Tc_mK, unit=u.K)
        >>> Tc_kuzmin = me.Entity("CurieTemperature", 0.1, description="Temperature estimated via Kuzmin model")

    """  # noqa: E501

    def __init__(
        self,
        ontology_label: str,
        value: numpy.typing.ArrayLike
        | mammos_units.Quantity
        | mammos_entity.Entity = 0,
        unit: str | None | mammos_units.UnitBase = None,
        description: str = "",
    ):
        self.description = description
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

        with u.set_enabled_aliases(
            # filtering units we do not want as default
            {"Cel": "K", "mCel": "K", "har": "m2"}
        ):
            si_unit = u.Unit(_extract_SI_units(ontology_label))

        if unit is None:
            # the user does not specify a unit:
            # so we initialize the entity with a SI ontology unit.
            with u.set_enabled_equivalencies(mammos_equivalencies):
                comp_si_unit = si_unit.decompose(bases=base_units)
            unit = u.CompositeUnit(1, comp_si_unit.bases, comp_si_unit.powers)

        else:
            # the user specify a unit:
            # we just check this unit is coherent with the ontology
            with u.set_enabled_equivalencies(mammos_equivalencies):
                if not si_unit.is_equivalent(unit):
                    raise u.UnitConversionError(
                        f"The unit '{unit}' is not equivalent to the unit of"
                        f" {ontology_label} '{si_unit}'"
                    )

        comp_unit = u.Unit(unit if unit else "")

        with u.set_enabled_equivalencies(mammos_equivalencies):
            self._quantity = u.Quantity(value=value, unit=comp_unit)
        self._ontology_label = ontology_label

    @property
    def description(self) -> str:
        """Additional description of the entity.

        The description is a string containing any information relevant to the entity.
        This can include, e.g., whether it is an experimentally measured or a simulated
        quantity, what techniques were used in its calculation, or the experimental
        precision.
        """
        return self._description

    @description.setter
    def description(self, value) -> None:
        if isinstance(value, str):
            self._description = value
        else:
            raise ValueError(
                "Description must be a string. "
                f"Received value: {value} of type: {type(value)}."
            )

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
        return self.quantity.value

    @property
    def unit(self) -> astropy.units.UnitBase:
        """Unit of the entity data."""
        return self.quantity.unit

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
        """Check if two Entities are identical.

        Entities are considered identical if they have the same ontology label and
        numerical data, i.e. unit prefixes have no effect.

        Equality ignores the ``description`` attribute.

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
        if not isinstance(other, self.__class__):
            return NotImplemented
        with u.set_enabled_equivalencies(mammos_equivalencies):
            return (
                self.ontology_label == other.ontology_label
                and self.q.shape == other.q.shape
                and u.allclose(self.q, other.q, equal_nan=True)
            )

    def __repr__(self) -> str:
        args = [f"ontology_label='{self._ontology_label}'", f"value={self.value!r}"]
        if str(self.unit):
            args.append(f"unit='{self.unit!s}'")
        if self.description:
            args.append(f"description={self.description!r}")

        return f"{self.__class__.__name__}({', '.join(args)})"

    def __str__(self) -> str:
        new_line = "\n" if self.value.size > 4 else ""
        repr_str = f"{self.ontology_label}(value={new_line}{self.value}"
        if not self.unit.is_equivalent(u.dimensionless_unscaled):
            repr_str += f",{new_line} unit={self.unit}"
        if self.description:
            repr_str += f",{new_line} description={self.description!r}"
        return repr_str + ")"

    def _repr_html_(self) -> str:
        html_str = str(self).replace("\n", "<br>").replace(" ", "&nbsp;")
        return f"<samp>{html_str}</samp>"

    def to_hdf5_dataset(self, base: h5py.File | h5py.Group, name: str) -> h5py.Dataset:
        """Write an entity to an HDF5 dataset.

        The value is added as data; ontology_label, iri, unit and description are
        written to the dataset attributes.
        """
        return me.io.to_hdf5(self, base, name)
