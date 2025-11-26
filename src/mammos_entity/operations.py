r"""Entities operations."""

from __future__ import annotations

import warnings
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
    description: str | None = None,
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
            entity. If not specified, all unique descriptions from the input entities
            are collected and concatenated. The order of the collected descriptions
            might change.

    Examples:
    >>> import mammos_entity as me
    >>> import mammos_units as u
    >>> Ms = me.Ms([500, 600], "kA/m")
    >>> me.concat_flat(Ms, 0.3, 700000 * u.A / u.m, unit="MA/m", description="Merge XRD and literature values")
    Entity(ontology_label='SpontaneousMagnetization', value=array([0.5, 0.6, 0.3, 0.7]), unit='MA / m', description='Merge XRD and literature values')

    """  # noqa: E501
    _elements = []
    _descriptions = [""]
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
            _descriptions.append(e.description)
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
    if description is None:
        warnings.warn(
            "concat_flat was called without specifying a description input. "
            "The descriptions from all entities are collected and concatenated "
            "into a single string.",
            stacklevel=1,
        )
        description = "".join(set(_descriptions))
    return me.Entity(
        ontology_labels[0], np.concatenate(values), unit, description=description
    )
