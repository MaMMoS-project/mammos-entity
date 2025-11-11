r"""Entities operations."""

from __future__ import annotations

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
    ontology label) and harmonises their units to match those in the `left` collection.
    The merged result is returned as a new `EntityCollection` that retains ontology
    labels and units where available.

    Args:
        left (EntityCollection):
            The primary `EntityCollection` whose ontology and units take precedence
            during the merge.
        right (EntityCollection):
            The secondary `EntityCollection` to merge with `left`.
        **kwargs:
            Additional keyword arguments passed to `pandas.merge()`
            (e.g., `on`, `how`, `left_on`, `right_on`, `suffixes`, etc.).

    Returns:
        EntityCollection:
            A new `EntityCollection` containing the merged data. Each entity retains
            ontology labels and units from the original collections when available.
    """
    # NOTE: pre-process entity collections for matching keys
    for key in set(left.__dict__.keys()) & set(right.__dict__.keys()):
        # NOTE: if left is entity:
        if isinstance(left_obj := getattr(left, key), me.Entity):
            # NOTE: if right is entity, check for label and units
            if isinstance(right_obj := getattr(right, key), me.Entity):
                # NOTE: different ontology -> raise error
                if left_obj.ontology_label != right_obj.ontology_label:
                    # left.__dict__.pop(key)
                    # right.__dict__.pop(key)
                    # setattr(left, f"{key}_{left_obj.ontology_label}", left_obj)
                    # setattr(right, f"{key}_{right_obj.ontology_label}", right_obj)
                    raise ValueError(
                        f"Cannot have the same entry {key} for entity "
                        f"with label {left_obj.ontology_label} in the left collection "
                        f"and label {right_obj.ontology_label} in the right collection."
                    )
                # NOTE: same ontology -> harmonise units
                elif (
                    left_obj.ontology_label == right_obj.ontology_label
                    and (lu := left_obj.unit) != right_obj.unit
                ):
                    setattr(
                        right,
                        key,
                        me.Entity(right_obj.ontology_label, right_obj.quantity.to(lu)),
                    )
            # NOTE: if right is quantity, check if the units match
            # if they do not, harmonise the units or raise error
            elif isinstance(right_obj := getattr(right, key), u.Quantity) and (
                lu := left_obj.unit
            ) != (ru := right_obj.unit):
                if lu.is_equivalent(ru):
                    setattr(right, key, right_obj.to(lu))
                else:
                    # left.__dict__.pop(key)
                    # right.__dict__.pop(key)
                    # setattr(left, f"{key}_{left_obj.unit}", left_obj)
                    # setattr(right, f"{key}_{right_obj.unit}", right_obj)
                    raise ValueError(
                        f"Cannot have different units for the entry {key} "
                        f"with unit {lu} in the left collection and "
                        f"unit {ru} in the right collection."
                    )
        # NOTE: if left is quantity
        # if right is an entity/quantity, check units
        # if the units do not match, harmonise/raise error
        elif (
            isinstance(left_obj := getattr(left, key), u.Quantity)
            and isinstance(right_obj := getattr(right, key), (me.Entity, u.Quantity))
            and (lu := left_obj.unit) != (ru := right_obj.unit)
        ):
            if lu.is_equivalent(ru):
                new_right_quantity = (
                    right_obj.to(lu)
                    if isinstance(right_obj, u.Quantity)
                    else right_obj.quantity.to(lu)
                )
                setattr(right, key, new_right_quantity)
            else:
                # left.__dict__.pop(key)
                # right.__dict__.pop(key)
                # setattr(left, f"{key}_{left_obj.unit}", left_obj)
                # setattr(right, f"{key}_{right_obj.unit}", right_obj)
                raise ValueError(
                    f"Cannot have different units for the entry {key} "
                    f"with unit {lu} in the left collection and "
                    f"unit {ru} in the right collection."
                )

    left_onto_info = {
        key: {
            "label": getattr(val, "ontology_label", None),
            "unit": getattr(val, "unit", None),
        }
        for key, val in left.__dict__.items()
    }
    right_onto_info = {
        key: {
            "label": getattr(val, "ontology_label", None),
            "unit": getattr(val, "unit", None),
        }
        for key, val in right.__dict__.items()
    }

    left_df = left.to_dataframe(include_units=False)
    right_df = right.to_dataframe(include_units=False)
    merged_df = pd.merge(left_df, right_df, **kwargs)

    result = me.io.EntityCollection()

    for key, val in merged_df.items():
        # NOTE: when the key from merged dataframe is not in info dictionaries
        if key not in left_onto_info and key not in right_onto_info:
            suffix_values = kwargs.get("suffixes", ["_x", "_y"])
            found_suffix = False
            if key.endswith(suffix_values[0]):
                key_new = key.removesuffix(suffix_values[0])
                found_suffix = True
            elif key.endswith(suffix_values[1]):
                key_new = key.removesuffix(suffix_values[1])
                found_suffix = True

            ontology_label = left_onto_info[key_new]["label"] if found_suffix else None
            unit = left_onto_info[key_new]["unit"] if found_suffix else None

        else:
            seleted_info_dict = (
                left_onto_info if key in left_onto_info else right_onto_info
            )
            ontology_label = seleted_info_dict[key]["label"]
            unit = seleted_info_dict[key]["unit"]

        if ontology_label:
            setattr(result, key, me.Entity(ontology_label, val.to_numpy(), unit))
        elif unit:
            setattr(result, key, u.Quantity(val.to_numpy(), unit))
        else:
            setattr(result, key, val.to_numpy())

    return result
