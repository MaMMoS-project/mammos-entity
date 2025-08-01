r"""Entities operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import mammos_units as u
import numpy as np

import mammos_entity as me

if TYPE_CHECKING:
    import numpy.typing

    import mammos_entity


def concat(
    *elements: mammos_entity.typing.EntityLike,
) -> mammos_entity.Entity:
    """Concatenate objects into a unique Entity.

    At least one of the inputs must be an Entity with a `ontology_label`.

    Converts all entries into the ontology-preferred unit.
    """
    ontology_labels = [e.ontology_label for e in elements if isinstance(e, me.Entity)]
    if not ontology_labels:
        raise ValueError("You must give at least one Entity.")
    elif len(set(ontology_labels)) > 1:
        raise ValueError("Entities with different labels were given.")
    unit = me.Entity(ontology_labels[0]).unit
    values = []
    for e in elements:
        if isinstance(e, me.Entity):
            values.append(e.q.flatten().to(unit))
        elif isinstance(e, u.Quantity):
            values.append(e.flatten().to(unit))
        else:
            values.append(np.asarray(e).flatten() * unit)
    return me.Entity(ontology_labels[0], np.concatenate(values), unit)
