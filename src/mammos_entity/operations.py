r"""Entities operations."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np
import pandas as pd

import mammos_entity as me

if TYPE_CHECKING:
    import typing

    import astropy
    import numpy.typing

    import mammos_entity


def concat_flat(
    *elements: mammos_entity.typing.EntityLike | list[typing.Any] | tuple[typing.Any],
    unit: astropy.units.Unit | str | None = None,
    description: str = "",
) -> mammos_entity.Entity:
    """Concatenate objects into a unique flat Entity.

    At least one of the inputs must be an Entity with a `ontology_label`.
    The unit of the first Entity is accepted unless the optional argument `unit` is
    defined.

    Arrays are flattened according to `np.flatten` in `order="C"`.

    Args:
        *elements: object arguments to be concatenated.
        unit: If specified, all objects are converted to this units or initialized with
            it.
        description: If specified, this description string is assigned to the resulting
            entity.

    Examples:
    >>> import mammos_entity as me
    >>> import mammos_units as u
    >>> Ms = me.Ms([500, 600], "kA/m")
    >>> me.concat_flat(Ms, 0.3, 700000 * u.A / u.m, unit="MA/m", description="Merge XRD and literature values")
    Entity(ontology_label='SpontaneousMagnetization', value=array([0.5, 0.6, 0.3, 0.7]), unit='MA / m', description='Merge XRD and literature values')
    """  # noqa: E501
    _elements = []
    for e in elements:
        if isinstance(e, list | tuple):
            _elements.extend(e)
        else:
            _elements.append(e)
    first_unit = None
    ontology_labels = []
    for e in _elements:
        if isinstance(e, me.Entity):
            if not first_unit:
                first_unit = e.unit
            ontology_labels.append(e.ontology_label)
    if not ontology_labels:
        raise ValueError("At least one Entity is required.")
    elif len(set(ontology_labels)) > 1:
        raise ValueError("Entities with different ontology labels are not supported.")
    unit = u.Unit(unit) if unit else first_unit
    values = []
    for e in _elements:
        if isinstance(e, me.Entity):
            values.append(e.q.flatten().to(unit))
        elif isinstance(e, u.Quantity):
            values.append(e.flatten().to(unit))
        else:
            values.append(np.asarray(e).flatten() * unit)
    return me.Entity(
        ontology_labels[0], np.concatenate(values), unit, description=description
    )


def merge(
    left: me.io.EntityCollection,
    right: me.io.EntityCollection,
    **kwargs,
) -> me.io.EntityCollection:
    """Merges two ``EntityCollection`` objects while preserving ontology and units.

    This function behaves similarly to ``pandas.merge``, but is aware of
    domain-specific metadata attached to each attribute in an ``EntityCollection``.
    It performs the following high-level steps:

    1. Deep-copy inputs so that neither ``left`` nor ``right`` is modified in-place.
    2. Determine a "preferred" collection based on the merge direction:
       - If ``how='right'`` is passed, ``right`` is treated as preferred.
       - Otherwise (including the default), ``left`` is preferred.
       The preferred collection defines the canonical ontology labels and units
       wherever there is a conflict.
    3. Pre-process overlapping attributes (same attribute name present in
       both collections) before calling ``pandas.merge``:
       - For overlapping attributes that are:
         * ``mammos_entity.Entity`` objects:
           - Ensures ontology labels match; if not, raises ``ValueError``.
           - Converts the non-preferred entity's unit to the preferred entity's unit.
           - Ensures the ontology label is preserved.
         * one ``mammos_entity.Entity`` and one ``mammos_units.Quantity``:
           - Ensures units are compatible; if not, raises ``ValueError``.
           - Wraps the quantity in an ``mammos_entity.Entity``, using the ontology label
             of the entity and the unit of the preferred side.
         * ``mammos_units.Quantity`` objects:
           - Ensures units are compatible; if not, raises ``ValueError``.
           - Converts the of quantity from the non-preferred unit to the preferred unit.
    4. Harmonize join keys if ``left_on`` and ``right_on`` are provided:
       - For corresponding pairs of join keys, it attempts to convert units of the
         non-preferred key to match the preferred key where:
         * Both sides are ``mammos_entity.Entity`` with identical ontology labels.
         * One side is ``mammos_entity.Entity`` and the other is a
           ``mammos_units.Quantity`` with compatible units.
       - This ensures that joins on physical quantities behave as expected
         (e.g. length in m vs cm).
    5. Perform a pandas-style merge on the plain DataFrame representations:
       - Uses ``EntityCollection.to_dataframe`` on both
         collections.
       - Calls ``pandas.merge`` with all remaining keyword arguments.
    6. Reconstruct a new ``EntityCollection`` from the merged DataFrame:
       - For each column in the merged DataFrame:
         * If the column corresponds to one of the original attributes
           (possibly with a suffix such as ``'_x'`` or ``'_y'``), the function
           restores the appropriate ontology label and unit using the original
           ``EntityCollection`` objects (with preference given to the preferred
           collection).
         * If the column does not originate from an ``mammos_entity.Entity`` or
           ``mammos_units.Quantity`` (e.g. an indicator column created by
           ``indicator=True``), it is stored as a plain NumPy array.
       - Any non-unit metadata (ontology labels) is preserved when possible.

    Args:
        left : The left-hand ``EntityCollection`` to merge. Unless ``how='right'`` is
               specified, this collection is treated as the preferred source of
               ontology labels and units for overlapping attributes.
        right : The right-hand ``EntityCollection`` to merge with. When ``how='right'``
                is used, this becomes the preferred collection for resolving ontology
                labels and units.
        **kwargs : Additional keyword arguments forwarded directly to ``pandas.merge``.

    Returns:
        mammos_entity.io.EntityCollection
            A new ``EntityCollection`` containing the merged data. Attribute types are:

            - ``mammos_entity.Entity`` for merged attributes that originated from entity
              instances or quantities with known ontology labels and units.
            - ``mammos_units.Quantity`` when unit information is known but there is no
              ontology label.
            - Plain NumPy arrays for columns without associated ontology or unit
              metadata.

            The returned collection does not share data with the input collections;
            both the input collections and their underlying data remain unchanged.

    Raises:
        ValueError
            If overlapping attributes have incompatible ontology labels or
            non-convertible units, for example:

            - Two entity attributes with different ``ontology_label`` values under
              the same attribute name.
            - Quantities with units that cannot be converted into each other
              (e.g. meters vs seconds).

    Example:
        >>> import mammos_entity as me
        >>> A_collection = me.io.EntityCollection(
        ...     x_pos=me.Entity("Length", [-10.0, -10.0, -10.0], "mm"),
        ...     y_pos=me.Entity("Length", [-10.0, -15.0, -20.0], "mm"),
        ...     a=me.Entity("LocalLatticeConstantA", [8.783, 8.783, 8.783], "Angstrom"),
        ...     c=me.Entity("LocalLatticeConstantC", [12.163, 12.162, 12.162], "Angstrom"),
        ...     volume=me.Entity("CellVolume", [938.468, 938.366, 938.321], "Angstrom^3"),
        ...     Ms=me.Ms([1205044.626, 1203469.633, 1202605.731]),
        ...     A=me.A([7.071, 7.053, 7.043], "pJ/m"),
        ...     K1=me.Ku([3.411, 3.388, 3.376], "MJ/m3"),
        ...     Ha=me.Entity(
        ...         "AnisotropyField",
        ...         [4505434.713, 4481343.844, 4468220.343],
        ...         "A/m",
        ...     ),
        ... )
        >>> B_collection = me.io.EntityCollection(
        ...     x_pos=me.Entity("Length", [-1, -1, -1], "cm"),
        ...     y_pos=me.Entity("Length", [-10.0, -15.0, -20.0], "mm"),
        ...     integral_abs_diff=[1.176, 1.174, 1.153],
        ... )
        >>> merged_collection = me.merge(A_collection, B_collection, how="inner")
        >>> merged_collection
        EntityCollection(
            x_pos=Entity(ontology_label='Length', value=array([-10., -10., -10.]), unit='mm'),
            y_pos=Entity(ontology_label='Length', value=array([-10., -15., -20.]), unit='mm'),
            a=Entity(ontology_label='LocalLatticeConstantA', value=array([8.783, 8.783, 8.783]), unit='Angstrom'),
            c=Entity(ontology_label='LocalLatticeConstantC', value=array([12.163, 12.162, 12.162]), unit='Angstrom'),
            volume=Entity(ontology_label='CellVolume', value=array([938.468, 938.366, 938.321]), unit='Angstrom3'),
            Ms=Entity(ontology_label='SpontaneousMagnetization', value=array([1205044.626, 1203469.633, 1202605.731]), unit='A / m'),
            A=Entity(ontology_label='ExchangeStiffnessConstant', value=array([7.071, 7.053, 7.043]), unit='pJ / m'),
            K1=Entity(ontology_label='UniaxialAnisotropyConstant', value=array([3.411, 3.388, 3.376]), unit='MJ / m3'),
            Ha=Entity(ontology_label='AnisotropyField', value=array([4505434.713, 4481343.844, 4468220.343]), unit='A / m'),
            integral_abs_diff=array([1.176, 1.174, 1.153]),
        )
    """  # noqa: E501
    # require deepcopy to ensure no modification of original EntityCollections
    left = deepcopy(left)
    right = deepcopy(right)

    if "how" in kwargs and kwargs["how"].lower() == "right":
        preferred_collection = right
        other_collection = left
    else:
        preferred_collection = left
        other_collection = right

    # pre-process entity collections for matching keys
    if "on" in kwargs and kwargs["on"]:
        matching_keys = set(kwargs["on"])
    else:
        matching_keys = set(preferred_collection.__dict__.keys()) & set(
            other_collection.__dict__.keys()
        )
    # check compatibility of entities and quantities and homogenize for merging:
    # - fail if the two entity_likes are not compatible
    # - convert all values to the units of the entity_like from the preferred collection
    # - preserve ontology_label if it is present in one of the two entity_likes
    for key in matching_keys:
        match (getattr(preferred_collection, key), getattr(other_collection, key)):
            case me.Entity() as pref_e, me.Entity() as other_e:
                if pref_e.ontology_label != other_e.ontology_label:
                    raise ValueError(
                        f"incompatible ontology labels for '{pref_e}' and '{other_e}'"
                    )
                setattr(
                    other_collection,
                    key,
                    me.Entity(pref_e.ontology_label, other_e.q.to(pref_e.unit)),
                )
            case me.Entity() as pref_e, u.Quantity() as other_q:
                if not pref_e.unit.is_equivalent(other_q.unit):
                    raise ValueError(
                        f"incompatible units for '{pref_e}' and '{other_q}'"
                    )
                setattr(
                    other_collection,
                    key,
                    me.Entity(pref_e.ontology_label, other_q.to(pref_e.unit)),
                )
            case u.Quantity() as pref_q, me.Entity() as other_e:
                if not pref_q.unit.is_equivalent(other_e.unit):
                    raise ValueError(
                        f"incompatible units for '{pref_q}' and '{other_e}'"
                    )
                setattr(
                    preferred_collection, key, me.Entity(other_e.ontology_label, pref_q)
                )
                setattr(
                    other_collection,
                    key,
                    me.Entity(other_e.ontology_label, other_e.q.to(pref_q.unit)),
                )
            case u.Quantity() as pref_q, u.Quantity() as other_q:
                if not pref_q.unit.is_equivalent(other_q.unit):
                    raise ValueError(
                        f"incompatible units for '{pref_q}' and '{other_q}'"
                    )
                setattr(other_collection, key, other_q.to(pref_q.unit))

    # harmonise units for left_on and right_on kwargs
    if {"left_on", "right_on"}.issubset(kwargs):
        if left is preferred_collection:
            pref_keys = (
                kwargs["left_on"]
                if not isinstance(kwargs["left_on"], str)
                else [kwargs["left_on"]]
            )
            other_keys = (
                kwargs["right_on"]
                if not isinstance(kwargs["right_on"], str)
                else [kwargs["right_on"]]
            )
        else:
            pref_keys = (
                kwargs["right_on"]
                if not isinstance(kwargs["right_on"], str)
                else [kwargs["right_on"]]
            )
            other_keys = (
                kwargs["left_on"]
                if not isinstance(kwargs["left_on"], str)
                else [kwargs["left_on"]]
            )

        for pref_key, other_key in zip(pref_keys, other_keys, strict=True):
            match (
                getattr(preferred_collection, pref_key),
                getattr(other_collection, other_key),
            ):
                case me.Entity() as pref_obj, me.Entity() as other_obj:
                    if pref_obj.ontology_label == other_obj.ontology_label:
                        setattr(
                            other_collection,
                            other_key,
                            me.Entity(
                                other_obj.ontology_label, other_obj.q.to(pref_obj.unit)
                            ),
                        )
                case me.Entity() as pref_obj, u.Quantity() as other_obj:
                    if pref_obj.unit.is_equivalent(other_obj.unit):
                        setattr(
                            other_collection, other_key, other_obj.to(pref_obj.unit)
                        )
                case u.Quantity() as pref_obj, me.Entity() as other_obj:
                    if pref_obj.unit.is_equivalent(other_obj.unit):
                        setattr(
                            other_collection,
                            other_key,
                            me.Entity(
                                other_obj.ontology_label, other_obj.q.to(pref_obj.unit)
                            ),
                        )

    # use left and right collections here because pandas will handle the
    # preference based on the `how` parameter.
    merged_df = pd.merge(
        left.to_dataframe(include_units=False),
        right.to_dataframe(include_units=False),
        **kwargs,
    )

    result = me.io.EntityCollection()

    suffix_values = kwargs.get("suffixes", ["_x", "_y"])

    for key, val in merged_df.items():
        # when the key from merged DataFrame is not in the collections
        key_with_suffix = None
        ontology_label = None
        unit = None
        if not (hasattr(preferred_collection, key) or hasattr(other_collection, key)):
            for i, suffix in enumerate(suffix_values):
                collection = left if i == 0 else right
                if key.endswith(suffix):
                    key_with_suffix = key
                    key = key.removesuffix(suffix)
                    obj = getattr(collection, key)
                    if isinstance(obj, me.Entity):
                        ontology_label = obj.ontology_label
                        unit = obj.unit
                    elif isinstance(obj, u.Quantity):
                        unit = obj.unit
                    break
            # when the key does not end with the defined suffixes
            # e.g. `indicator=True` for pandas merge function
            if not key_with_suffix:
                setattr(result, key, val)
                continue

        if key in matching_keys:
            pref_obj = getattr(preferred_collection, key)
            other_obj = getattr(other_collection, key)

            if (pref_entity := isinstance(pref_obj, me.Entity)) or isinstance(
                other_obj, me.Entity
            ):
                selected_obj = pref_obj if pref_entity else other_obj
                ontology_label = selected_obj.ontology_label
                unit = selected_obj.unit
            elif (pref_quantity := isinstance(pref_obj, u.Quantity)) or isinstance(
                other_obj, u.Quantity
            ):
                unit = pref_obj.unit if pref_quantity else other_obj.unit
        else:
            obj = (
                getattr(preferred_collection, key)
                if hasattr(preferred_collection, key)
                else getattr(other_collection, key)
            )
            if isinstance(obj, me.Entity) and ontology_label is None:
                ontology_label = obj.ontology_label
                unit = obj.unit
            elif isinstance(obj, u.Quantity) and unit is None:
                unit = obj.unit

        key = key_with_suffix if key_with_suffix else key
        if ontology_label:
            setattr(result, key, me.Entity(ontology_label, val.to_numpy(), unit))
        elif unit:
            setattr(result, key, u.Quantity(val.to_numpy(), unit))
        else:
            setattr(result, key, val.to_numpy())
    return result
