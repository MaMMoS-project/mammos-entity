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
    if "how" in kwargs and kwargs["how"].lower() == "right":
        preferred_collection = right
        other_collection = left
    else:
        preferred_collection = left
        other_collection = right
    # NOTE: pre-process entity collections for matching keys
    for key in set(preferred_collection.__dict__.keys()) & set(
        other_collection.__dict__.keys()
    ):
        # NOTE: if preferred collection object is entity:
        if isinstance(pref_obj := getattr(preferred_collection, key), me.Entity):
            # NOTE: if other collection object is entity, check for label and units
            if isinstance(other_obj := getattr(other_collection, key), me.Entity):
                # NOTE: different ontology -> raise error
                if pref_obj.ontology_label != other_obj.ontology_label:
                    # preferred_collection.__dict__.pop(key)
                    # other_collection.__dict__.pop(key)
                    # setattr(
                    #     preferred_collection,
                    #     f"{key}_{pref_obj.ontology_label}",
                    #     pref_obj
                    # )
                    # setattr(
                    #     other_collection,
                    #     f"{key}_{other_obj.ontology_label}",
                    #     other_obj
                    # )
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
                    # preferred_collection.__dict__.pop(key)
                    # other_collection.__dict__.pop(key)
                    # setattr(preferred_collection, f"{key}_{pref_obj.unit}", pref_obj)
                    # setattr(other_collection, f"{key}_{other_obj.unit}", other_obj)
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
                    else other_obj.quantity.to(pu)
                )
                setattr(other_collection, key, new_other_quantity)
            else:
                # preferred_collection.__dict__.pop(key)
                # other_collection.__dict__.pop(key)
                # setattr(preferred_collection, f"{key}_{pref_obj.unit}", pref_obj)
                # setattr(other_collection, f"{key}_{other_obj.unit}", other_obj)
                raise ValueError(
                    f"Cannot have different units for the entry {key} "
                    f"with unit {pu} in the {preferred_collection} and "
                    f"unit {ou} in the {other_collection}."
                )

    pref_onto_info = {
        key: {
            "label": getattr(val, "ontology_label", None),
            "unit": getattr(val, "unit", None),
        }
        for key, val in preferred_collection.__dict__.items()
    }
    other_onto_info = {
        key: {
            "label": getattr(val, "ontology_label", None),
            "unit": getattr(val, "unit", None),
        }
        for key, val in other_collection.__dict__.items()
    }

    merged_df = pd.merge(
        left.to_dataframe(include_units=False),
        right.to_dataframe(include_units=False),
        **kwargs,
    )

    result = me.io.EntityCollection()

    for key, val in merged_df.items():
        # NOTE: when the key from merged DataFrame is not in info dictionaries
        if key not in pref_onto_info and key not in other_onto_info:
            suffix_values = kwargs.get("suffixes", ["_x", "_y"])
            found_suffix = False
            if key.endswith(suffix_values[0]):
                key_new = key.removesuffix(suffix_values[0])
                selected_info_dict = pref_onto_info
                found_suffix = True
            elif key.endswith(suffix_values[1]):
                key_new = key.removesuffix(suffix_values[1])
                selected_info_dict = other_onto_info
                found_suffix = True

            ontology_label = (
                selected_info_dict[key_new]["label"] if found_suffix else None
            )
            unit = selected_info_dict[key_new]["unit"] if found_suffix else None

        else:
            seleted_info_dict = (
                pref_onto_info if key in pref_onto_info else other_onto_info
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
