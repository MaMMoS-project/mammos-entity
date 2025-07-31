from typing import Annotated

import mammos_units as u
import numpy.typing as npt
import ontopy
import pytest

import mammos_entity as me


def test_entity_like_generic():
    assert (
        me.typing.EntityLike["SpontaneousMagnetization"]
        == Annotated[me.Entity | u.Quantity | npt.ArrayLike, "SpontaneousMagnetization"]
    )
    with pytest.raises(ontopy.utils.NoSuchLabelError):
        me.typing.EntityLike["NotInTheOntology"]
    with pytest.raises(TypeError):
        me.typing.EntityLike[1]
