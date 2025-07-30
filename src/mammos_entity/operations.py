r"""Entities operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np

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
