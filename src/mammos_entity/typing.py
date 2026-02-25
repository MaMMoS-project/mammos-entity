"""Type aliases for static type annotations."""

from typing import TypeAlias

import astropy.units
import numpy.typing

import mammos_entity
from mammos_entity._typevars import OntologyLabelT as _OntologyLabelT

#: Type variable for ontology labels used in public typing annotations.
#:
#: In user-facing annotations this is typically specialized with
#: ``typing.Literal[...]``, for example ``Entity[Literal["CurieTemperature"]]``.
OntologyLabelT = _OntologyLabelT

__all__ = ["OntologyLabelT", "EntityLike"]

EntityLike: TypeAlias = (
    mammos_entity.Entity[OntologyLabelT]
    | astropy.units.Quantity
    | numpy.typing.ArrayLike
)
"""Any object that can be interpreted as an entity. Besides entities, this includes
quantities and raw numbers (scalar or array-like). The latter two are interpreted as
the quantity or value of the required entity, respectively, if a function expects a
specific entity.
"""
