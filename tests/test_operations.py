"""Test operations module."""

import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me


def test_concat_flat():
    """Test concat operation."""
    e_1 = me.Ms(1)
    e_2 = me.Ms(2)
    assert me.concat_flat(e_1, e_2) == me.Ms([1, 2])
    assert me.concat_flat(e_1, e_1, e_2) == me.Ms([1, 1, 2])
    assert me.concat_flat(e_1, 4) == me.Ms([1, 4])
    assert me.concat_flat(4, e_1) == me.Ms([4, 1])
    assert me.concat_flat(e_1, [[2], [3]]) == me.Ms([1, 2, 3])
    e_3 = me.Ms([1, 2])
    assert me.concat_flat(e_3, e_1, 4) == me.Ms([1, 2, 1, 4])
    ee = [e_1, e_2, e_3]
    assert me.concat_flat(*ee) == me.Ms([1, 2, 1, 2])
    assert me.concat_flat(*ee, 3) == me.Ms([1, 2, 1, 2, 3])
    e_4 = me.Ms(1, unit=u.kA / u.m)
    assert me.concat_flat(e_1, e_4) == me.Ms([1, 1000])
    assert me.concat_flat(e_4, e_4) == me.Ms([1, 1], unit=u.kA / u.m)
    assert me.concat_flat(e_4, e_4).unit == u.kA / u.m
    assert np.allclose(me.concat_flat(e_4, e_4, unit=u.mA / u.m).value, [1e6, 1e6])
    assert me.concat_flat(e_4, e_4, unit=u.mA / u.m).unit == u.mA / u.m
    assert me.concat_flat(me.Ms([[1, 2], [3, 4]]), 5) == me.Ms([1, 2, 3, 4, 5])
    assert me.concat_flat([e_1, e_2]) == me.Ms([1, 2])
    assert me.concat_flat([e_1, 2]) == me.Ms([1, 2])
    assert me.concat_flat(e_1, 3 * u.A / u.m)


def test_failing_concat():
    """Test concat operation supposed to fail."""
    with pytest.raises(ValueError):
        me.concat_flat()
    with pytest.raises(ValueError):
        me.concat_flat(1, 2)
    with pytest.raises(ValueError):
        me.concat_flat([1, 2] * u.m, 3)
    with pytest.raises(ValueError):
        me.concat_flat(me.Ms(1), me.Js(2))
