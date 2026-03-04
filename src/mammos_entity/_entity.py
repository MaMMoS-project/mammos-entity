"""Define the core `Entity` class.

Defines the core `Entity` class to link physical quantities to ontology concepts. Also
includes helper functions for inferring the correct SI units from the ontology.

"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import h5py
import mammos_units as u

import mammos_entity as me
from mammos_entity._ontology import mammos_ontology, search_labels

if TYPE_CHECKING:
    import astropy.units
    import mammos_units
    import numpy.typing
    import owlready2

    import mammos_entity


base_units = [u.T, u.J, u.m, u.A, u.radian, u.kg, u.s, u.K, u.mol, u.cd, u.V]
mammos_equivalencies = u.temperature()


def _convert_unit(
    ontology_unit: owlready2.entity.ThingClass,
) -> astropy.units.UnitBase | None:
    """Convert ontology unit to astropy unit.

    This function reads the function Unified Code for Units of Measure (UCUM) code and
    creates an astropy Unit with such code.

    Round and square brackets are not recognized by Astropy, so codes with them are
    filtered off.

    Args:
        ontology_unit: Ontology entry for a specific unit.

    Returns:
        Astropy unit associated with the ontology entry, if found.
        This function can return `None` if the entity gives no UCUM code,
        or the UCUM code cannot be processed by astropy.

    Examples:
        >>> import mammos_entity as me
        >>> me._entity._convert_unit(me.mammos_ontology.AmperePerMetre)
        Unit("A / m")

    """
    for code in ontology_unit.ucumCode:
        if "(" not in code and "[" not in code:
            with u.set_enabled_aliases(
                {
                    # mapping {UCUM: astropy} for non-coherent unit codes
                    "Cel": u.Celsius,  # degree Celsius
                    "{#}": u.dimensionless_unscaled,  # number
                }
            ):
                unit = u.Unit(code)
                return unit


def _convert_dimension_string(unit_string: str) -> astropy.units.UnitBase:
    """Convert an ontology dimension string into astropy units.

    In particular, this conversion takes a dimension string of ISQ base quantities
    and converts it to its ISO unit symbols, returning a unit object from astropy.

    Args:
        unit_string: The string representation of the ISQ base quantities.

    Returns:
        The Astropy unit.

    Examples:
        >>> import mammos_entity as me
        >>> me._entity._convert_dimension_string('T0 L+2 M0 I+1 Θ0 N0 J0')
        Unit("m2 A")

    """
    unit_map = {
        "T": "s",
        "L": "m",
        "M": "kg",
        "I": "A",
        "Θ": "K",
        "N": "mol",
        "J": "cd",
    }

    # Parse the unit string into a list of (base_unit, exponent) tuples
    ISQ_list = re.findall(r"([TLMIΘNJ])([+-]?\d+)", unit_string)

    # Create composite unit from list of (ISQ_dimension, exponent)
    bases = [getattr(u, unit_map[u_[0]]) for u_ in ISQ_list]
    exponents = [int(u_[1]) for u_ in ISQ_list]
    astropy_unit = u.CompositeUnit(1, bases, exponents)
    return astropy_unit


def _get_all_possible_units(ontology_label: str) -> list[astropy.units.UnitBase]:
    """Get list of accepted units given an ontology label found in the ontology.

    Given a label for an ontology entry, this function finds all SI base units,
    SI-coherent units, and some selected special units (classified as
    `SISpecialUnit` in the EMMO ontology), navigating the class hierarchy.

    In case the ontology does not define concrete units (e.g. `Meter`) as subclasses
    of a certain abstract unit (e.g. `LengthUnit`), we define the unit using the
    dimension string specified in the `hasDimensionString` attribute of the abstract
    unit.

    Args:
        ontology_label: The label of an ontology concept
            (e.g., 'SpontaneousMagnetization').

    Returns:
        A list of all compatible astropy units.

    Examples:
        >>> import mammos_entity as me
        >>> me._entity._get_all_possible_units("ThermodynamicTemperature")
        [Unit("K"), Unit("deg_C")]

    """
    thing = me.mammos_ontology[ontology_label]
    possible_units = []
    for ancestor in thing.ancestors():
        # we find the ancestor with the attribute `hasMeasurementUnit`
        if hasattr(ancestor, "hasMeasurementUnit") and ancestor.hasMeasurementUnit:
            measurement_unit = ancestor.hasMeasurementUnit[0]
            if (
                measurement_unit == mammos_ontology.DimensionlessUnit
                or mammos_ontology.DimensionlessUnit in measurement_unit.ancestors()
            ):
                # entity is dimensionless by ontology
                possible_units.append(u.Unit(""))
            elif all_sub_classes := list(ancestor.hasMeasurementUnit[0].subclasses()):
                for sub_class in all_sub_classes:
                    # We extract only SI base units, coherent units and special units.
                    # See https://emmo-repo.github.io/emmo.html#siunit
                    if isinstance(
                        sub_class,
                        (
                            mammos_ontology.SIBaseUnit,
                            mammos_ontology.SICoherentDerivedUnit,
                            mammos_ontology.SISpecialUnit,
                        ),
                    ):
                        converted_unit = _convert_unit(sub_class)
                        if converted_unit is not None:
                            possible_units.append(converted_unit)
                if len(possible_units) == 0:
                    # Possible case: the abstract unit only points to non-SI
                    # concrete units. We use Astropy to read the dimension string.
                    possible_units.append(
                        _convert_dimension_string(
                            ancestor.hasMeasurementUnit[0].hasDimensionString
                        )
                    )
            else:
                # Extreme case: the ancestor has the attribute `hasMeasurementUnit` (the
                # abstract unit), but it defines to subclasses (the concrete units).
                # In this case, we create a Astropy unit directly from the dimension
                # string.
                possible_units.append(
                    _convert_dimension_string(
                        ancestor.hasMeasurementUnit[0].hasDimensionString
                    )
                )
            break
    else:
        # The only alternative is that the ontology concept is not related
        # to a quantifiable physical entity. So its unit is dimensionless.
        possible_units.append(u.Unit(""))
    return sorted(possible_units, key=str)  # return sorted to guarantee reproducibility


def _get_preferred_unit(
    possible_units: list[astropy.units.UnitBase],
) -> astropy.units.UnitBase:
    """Choose a preferred unit from a list of possible units.

    If among the possible units there is Kelvin, we always choose it instead of degree
    Celsius. Otherwise, as the default method of preference we choose the shortest
    possible unit formulation in base units.

    Args:
        possible_units: list of astropy units compatible with ontology.

    Returns:
        Chosen astropy unit.

    Examples:
        >>> import mammos_entity as me
        >>> import mammos_units as u
        >>> me._entity._get_preferred_unit([u.Unit("m2"), u.Unit("m2 sr"), u.Unit("mm2"), u.Unit("m2 / sr")])
        Unit("m2")

        >>> me._entity._get_preferred_unit([u.Unit("deg_C"), u.Unit("0.001 deg_C"), u.Unit("K")])
        Unit("K")

    """  # noqa:E501
    if u.Unit("K") in possible_units:
        return u.Unit("K")
    if len(possible_units) == 1:
        return possible_units[0]
    rescaled_units = []
    for _unit in possible_units:
        decomposed_unit = _unit.decompose(bases=base_units)
        rescaled_unit = u.CompositeUnit(
            1,
            decomposed_unit.bases,
            decomposed_unit.powers,
        )
        rescaled_units.append(rescaled_unit)
    out = sorted(set(rescaled_units), key=lambda x: len(str(x)))[0]
    return out


def _select_ontology_label(label: str) -> str:
    """Select ontology label from given one.

    First, the label is matched with the `prefLabel`s in the ontology. If the given
    label does not match with any `prefLabel`, we use the function
    :py:func:`~mammos.entity.search_labels` to also match `label`s and `altLabel`s.

    If any of these two step returns more than one match, an error is raised.

    Args:
        label: Given label of an ontology entry.

    Returns:
        Matched label in the ontology.

    Raises:
        ValueError: Multiple ontology entries have the selected entry as prefLabel.
        ValueError: No ontology entry found to match to given label.
        ValueError: The given label is not the prefLabel for any ontology entry and it
            is ambiguous as an alternative label.

    """
    # Find prefLabel
    prefLabel_matches = mammos_ontology.search(prefLabel=label)
    n_matches = len(prefLabel_matches)
    if n_matches == 1:
        return str(prefLabel_matches[0].prefLabel[0])
    elif n_matches > 1:
        raise ValueError(
            f"The ontology contains more than one entry with the given label '{label}' "
            "as prefLabel. Please raise an issue in the mammos-entity repository "
            "https://github.com/MaMMoS-project/mammos-entity/issues or in the "
            "repository of the relevant ontology."
        )

    # Find alternative labels
    label_matches = search_labels(label, auto_wildcard=False)
    n_matches = len(label_matches)
    if n_matches == 1:
        return label_matches[0]
    elif n_matches == 0:
        raise ValueError(f"No ontology entry found with label '{label}'.")
    else:
        raise ValueError(
            f"The given label '{label}' is ambiguous. It is not the prefLabel for any "
            "entry in the ontology and it appears as alternative label for multiple "
            f"entries: {label_matches}. Please use a prefLabel instead."
        )


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
        value: mammos_entity.Entity
        | mammos_units.Quantity
        | numpy.typing.ArrayLike = 0,
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

        # Select ontology label
        label = _select_ontology_label(ontology_label)

        # Get ontology-compatible units
        ontology_units = _get_all_possible_units(label)

        if unit is None:
            if isinstance(value, u.Quantity):
                # No explicit unit is given, but `value` is a Quantity:
                # we take the unit of `value`
                unit = value.unit
            else:
                # the user does not specify a unit: we choose the most frequent unit.
                unit = _get_preferred_unit(ontology_units)
        else:
            unit = u.Unit(unit)

        with u.set_enabled_equivalencies(mammos_equivalencies):
            if not any(unit.is_equivalent(ou) for ou in ontology_units):
                raise ValueError(
                    f"Given unit: {unit} incompatible with ontology. "
                    f"Allowed units for entity {label} are: {ontology_units}."
                )

            self._quantity = u.Quantity(value=value, unit=unit)
        self._ontology_label = label

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
            The ontology label corresponding to the right ThingClass.

        """
        return self._ontology_label

    @property
    def ontology_iri(self) -> str:
        """The ontology IRI that links the entity to the EMMO ontology.

        Retrieve the ontology IRI (Internationalized Resource Identifier) corresponding
        to the `ThingClass` that defines the given entity in ontology.

        Returns:
            The ontology IRI corresponding to the right ThingClass.

        """
        return self.ontology.iri

    @property
    def ontology_label_with_iri(self) -> str:
        """The ontology label with its IRI. Unique link to EMMO ontology.

        Returns the `self.ontology_label` together with the IRI (a URL that
        points to the definition of this entity.) IRI stands for
        Internationalized Resource Identifier.

        Returns:
            The ontology label corresponding to the right ThingClass, together with the
            IRI.

        """
        return f"{self.ontology_label} {self.ontology_iri}"

    # FIX: right not this will fail if no internet!
    @property
    def ontology(self) -> owlready2.entity.ThingClass:
        """Retrieve the ontology class corresponding to the entity's label.

        Returns:
            The ontology class from `mammos_ontology` that matches the entity's label.

        """
        return mammos_ontology.get_by_label(self.ontology_label)

    @property
    def quantity(self) -> mammos_units.Quantity:
        """Return the value and unit of the entity as a Quantity.

        Return a stand-alone :py:class:`~mammos_units.Quantity` object with the same
        value and unit, detached from the ontology link.

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
    def unit(self) -> mammos_units.UnitBase:
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

    def to_hdf5(
        self,
        base: h5py.File | h5py.Group | str | os.PathLike,
        name: str,
    ) -> h5py.Dataset | None:
        """Write an entity to an HDF5 dataset.

        The value is added as data of the dataset; ontology_label, iri, unit and
        description are written to the dataset attributes.

        Args:
            base: If it is an open HDF5 file or a group in an HDF5 file, data will be
                added to it as new dataset. If it is a str or PathLike a new HDF5 file
                with the given name will be created. If a file with that name exists
                already, it will be overwritten without notice.
            name: Name for the newly created dataset. If an element with that name
                exists already in `base` the function will fail.

        Returns:
            If `base` is an open `File` or `Group` the newly created dataset. If `base`
            is a file name nothing is returned (because the file created internally will
            be closed before the function returns).
        """
        return self._to_hdf5(base, name)

    def _to_hdf5(
        self,
        base: h5py.File | h5py.Group | str | os.PathLike,
        name: str,
        record_mammos_entity_version: bool = True,
    ) -> h5py.Dataset | None:
        """Internal implementation with additional options required for recursion.

        Args:
            base: <see public function>
            name: <see public function>
            record_mammos_entity_version: add mammos_entity version to dataset
                attributes.
        """
        if isinstance(base, str | os.PathLike):
            with h5py.File(base, "w") as f:
                self._to_hdf5(f, name, record_mammos_entity_version)
                return

        dset = base.create_dataset(name, data=self.value)
        dset.attrs["ontology_label"] = self.ontology_label
        dset.attrs["ontology_iri"] = self.ontology.iri
        dset.attrs["unit"] = str(self.unit)
        dset.attrs["description"] = self.description

        if record_mammos_entity_version:
            dset.attrs["mammos_entity_version"] = me.__version__
        return dset
