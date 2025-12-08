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
        left: The given `EntityCollection`.
        right: The `EntityCollection` to merge with.
        **kwargs: Additional keyword arguments passed to `pandas.merge()`
                  (e.g., `on`, `how`, `left_on`, `right_on`, `suffixes`, etc.).

    Returns:
        EntityCollection: A new `EntityCollection` containing the merged data. Each
                          entity retains ontology labels and units from the original
                          collections when available.
    """
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
        if not (hasattr(preferred_collection, key) or hasattr(other_collection, key)):
            for suffix in suffix_values:
                if key.endswith(suffix):
                    key_with_suffix = key
                    key.removesuffix(suffix)
                    break
            # when the key does not end with the defined suffixes
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
            setattr(result, key, me.Entity(ontology_label, val.to_numpy(), unit))
        elif unit:
            setattr(result, key, u.Quantity(val.to_numpy(), unit))
        else:
            setattr(result, key, val.to_numpy())
    return result
