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
) -> mammos_entity.Entity:
    """Concatenate objects into a unique flat Entity.

    At least one of the inputs must be an Entity with a `ontology_label`.
    The unit of the first Entity is accepted unless the optional argument `unit` is
    defined.

    Arrays are flattened according to `np.flatten` in `order="C"`.
    """
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
    if not unit:
        unit = first_unit
    values = []
    for e in _elements:
        if isinstance(e, me.Entity):
            values.append(e.q.flatten().to(unit))
        elif isinstance(e, u.Quantity):
            values.append(e.flatten().to(unit))
        else:
            values.append(np.asarray(e).flatten() * unit)
    return me.Entity(ontology_labels[0], np.concatenate(values), unit)


def merge(
    left: me.io.EntityCollection,
    right: me.io.EntityCollection,
    **kwargs,
) -> me.io.EntityCollection:
    """Merges two `EntityCollection` objects while preserving ontology and units.

    This function merges two `EntityCollection` instances in a dataframe-like manner.
    Before merging, it identifies overlapping entities (i.e., attributes with the same
    ontology label) and harmonizes their units, as well as, tries to carry forward
    as much metadata as possible. The merged result is returned as a new
    `EntityCollection` that retains ontology labels and units where available.

    Args:
        left (EntityCollection):
            The given `EntityCollection`.
        right (EntityCollection):
            The `EntityCollection` to merge with.
        **kwargs:
            Additional keyword arguments passed to `pandas.merge()`
            (e.g., `on`, `how`, `left_on`, `right_on`, `suffixes`, etc.).

    Returns:
        EntityCollection:
            A new `EntityCollection` containing the merged data. Each entity retains
            ontology labels and units from the original collections when available.
    """
    # NOTE: require deepcopy to ensure no modification of original EntityCollections
    left = deepcopy(left)
    right = deepcopy(right)

    if "how" in kwargs and kwargs["how"].lower() == "right":
        preferred_collection = right
        other_collection = left
    else:
        preferred_collection = left
        other_collection = right

    # NOTE: pre-process entity collections for matching keys
    matching_keys = set(preferred_collection.__dict__.keys()) & set(
        other_collection.__dict__.keys()
    )
    for key in matching_keys:
        # NOTE: if preferred collection object is entity:
        if isinstance(pref_obj := getattr(preferred_collection, key), me.Entity):
            # NOTE: if other collection object is entity, check for label and units
            if isinstance(other_obj := getattr(other_collection, key), me.Entity):
                # NOTE: different ontology -> raise error
                if pref_obj.ontology_label != other_obj.ontology_label:
                    raise ValueError(
                        f"Cannot have the same entry {key} for entity "
                        f"with label {pref_obj.ontology_label} in the "
                        f"{preferred_collection} and label "
                        f"{other_obj.ontology_label} in the {other_collection}."
                    )
                # NOTE: same ontology -> harmonise units
                elif (
                    pref_obj.ontology_label == other_obj.ontology_label
                    and (pu := pref_obj.unit) != other_obj.unit
                ):
                    setattr(
                        other_collection,
                        key,
                        me.Entity(other_obj.ontology_label, other_obj.quantity.to(pu)),
                    )
            # NOTE: if other object is quantity, check if the units match
            # if they do not, harmonise the units or raise error
            elif isinstance(
                other_obj := getattr(other_collection, key), u.Quantity
            ) and (pu := pref_obj.unit) != (ou := other_obj.unit):
                if pu.is_equivalent(ou):
                    setattr(other_collection, key, other_obj.to(pu))
                else:
                    raise ValueError(
                        f"Cannot have different units for the entry {key} "
                        f"with unit {pu} in the {preferred_collection} and "
                        f"unit {ou} in the {other_collection}."
                    )
        # NOTE: if preferred collection is quantity
        # if other collection is an entity/quantity, check units
        # if the units do not match, harmonise/raise error
        elif (
            isinstance(pref_obj := getattr(preferred_collection, key), u.Quantity)
            and isinstance(
                other_obj := getattr(other_collection, key), (me.Entity, u.Quantity)
            )
            and (pu := pref_obj.unit) != (ou := other_obj.unit)
        ):
            if pu.is_equivalent(ou):
                new_other_quantity = (
                    other_obj.to(pu)
                    if isinstance(other_obj, u.Quantity)
                    else me.Entity(other_obj.ontology_label, other_obj.quantity.to(pu))
                )
                setattr(other_collection, key, new_other_quantity)
            else:
                raise ValueError(
                    f"Cannot have different units for the entry {key} "
                    f"with unit {pu} in the {preferred_collection} and "
                    f"unit {ou} in the {other_collection}."
                )

    # NOTE: use left and right collections here because pandas will handle the
    # preference based on the `how` parameter.
    merged_df = pd.merge(
        left.to_dataframe(include_units=False),
        right.to_dataframe(include_units=False),
        **kwargs,
    )

    result = me.io.EntityCollection()

    suffix_values = kwargs.get("suffixes", ["_x", "_y"])

    for key, val in merged_df.items():
        # NOTE: when the key from merged DataFrame is not in the collections
        key_with_suffix = None
        if not (hasattr(preferred_collection, key) or hasattr(other_collection, key)):
            for suffix in suffix_values:
                if key.endswith(suffix):
                    key_with_suffix = key
                    key.removesuffix(suffix)
                    break
            # NOTE: when the key does not end with the defined suffixes
            # e.g. `indicator=True` for pandas merge function
            else:
                setattr(result, key, val)
                continue

        ontology_label = None
        unit = None
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
            if isinstance(obj, me.Entity):
                ontology_label = obj.ontology_label
                unit = obj.unit
            elif isinstance(obj, u.Quantity):
                unit = obj.unit

        key = key_with_suffix if key_with_suffix else key
        if ontology_label:
            setattr(result, key, me.Entity(ontology_label, val, unit))
        elif unit:
            setattr(result, key, u.Quantity(val, unit))
        else:
            setattr(result, key, val)
    return result
