from typing import TypeAlias

import astropy.units
import numpy.typing

import mammos_entity

EntityLike: TypeAlias = (
    mammos_entity.Entity | astropy.units.Quantity | numpy.typing.ArrayLike
)
"""Any object that can be interpreted as an entity. Besides entities, this includes
quantities and raw numbers (scalar or array-like). The latter two are interpreted as
the quantity or value of the required entity, respectively, if a function expects a
specific entity.
"""
