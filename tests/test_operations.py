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


def test_merge_no_intersections():
    """Test merge function."""
    ec_1 = me.io.EntityCollection(
        Ms=me.Ms([1, 1]),
    )
    ec_2 = me.io.EntityCollection(
        A=me.A([2, 2]),
    )
    ec_merged = me.merge(ec_1, ec_2)
    ec_check = me.io.EntityCollection(Ms=me.Ms([1, 1]), A=me.A([2, 2]))
    assert ec_merged.Ms == ec_check.Ms
    assert ec_merged.A == ec_check.A


def test_merge_inner():
    """Test "inner" merge function.

    By default, if two entity collections have any intersection we expect the merge
    function to use the flag `how="inner"`.
    """
    ec_1 = me.io.EntityCollection(
        x=[1, 2, 3, 3], y=[1, 1, 3, 3], Ms=me.Ms([1, 2, 3, 3.5])
    )
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4, 3],
        y=[1, 3, 5, 7],
        A=me.A([22, 33, 44, 33.55]),
    )
    ec_merged_1 = me.merge(ec_1, ec_2, on="x", how="inner")
    ec_check_1 = me.io.EntityCollection(
        x=np.array([2, 3, 3, 3, 3]),
        y_x=np.array([1, 3, 3, 3, 3]),
        y_y=np.array([1, 3, 7, 3, 7]),
        Ms=me.Ms([2, 3, 3, 3.5, 3.5]),
        A=me.A([22, 33, 33.55, 33, 33.55]),
    )
    assert np.all(ec_merged_1.x == ec_check_1.x)
    assert np.all(ec_merged_1.y_x == ec_check_1.y_x)
    assert np.all(ec_merged_1.y_y == ec_check_1.y_y)
    assert ec_merged_1.Ms == ec_check_1.Ms
    assert ec_merged_1.A == ec_check_1.A

    ec_merged_2 = me.merge(ec_1, ec_2, on=["x", "y"], how="inner")
    ec_check_2 = me.io.EntityCollection(
        x=np.array([2, 3, 3]),
        y=np.array([1, 3, 3]),
        Ms=me.Ms([2, 3, 3.5]),
        A=me.A([22, 33, 33]),
    )
    assert np.all(ec_merged_2.x == ec_check_2.x)
    assert ec_merged_2.Ms == ec_check_2.Ms
    assert ec_merged_2.A == ec_check_2.A


def test_merge_inner_overlap():
    """Test inner merge function with overlapping columns."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        Ms=me.Ms([22, 33, 44]),
    )
    ec_merged_1 = me.merge(ec_1, ec_2, on="x")
    ec_check_1 = me.io.EntityCollection(
        x=np.array([2, 3]),
        Ms_x=me.Ms([2, 3]),
        Ms_y=me.Ms([22, 33]),
    )
    assert np.all(ec_merged_1.x == ec_check_1.x)
    assert ec_merged_1.Ms_x == ec_check_1.Ms_x
    assert ec_merged_1.Ms_y == ec_check_1.Ms_y

    ec_merged_2 = me.merge(ec_1, ec_2, on="x", suffixes=("_1", "_2"))
    ec_check_2 = me.io.EntityCollection(
        x=np.array([2, 3]),
        Ms_1=me.Ms([2, 3]),
        Ms_2=me.Ms([22, 33]),
    )
    assert np.all(ec_merged_2.x == ec_check_2.x)
    assert ec_merged_2.Ms_1 == ec_check_2.Ms_1
    assert ec_merged_2.Ms_2 == ec_check_2.Ms_2

    with pytest.raises(ValueError):
        me.merge(ec_1, ec_2, on="x", suffixes=(None, None))


def test_merge_inner_overlap_empty():
    """Test inner merge function with overlapping columns.

    If merged without specifying the attribute `on`, the merge is calculated on
    all the common columns. We generated a entity collection corresponding to an empty
    DataFrame and we check that the attributes have disappeared.
    """
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        Ms=me.Ms([22, 33, 44]),
    )

    ec_merged_empty = me.merge(ec_1, ec_2)
    assert not hasattr(ec_merged_empty, "x")
    assert not hasattr(ec_merged_empty, "Ms")


def test_merge_inner_different_units():
    """Test inner merge function with different units."""
    ec_1 = me.io.EntityCollection(
        x=[1, 2, 3] * u.m,
        Ms=me.Ms([1, 2, 3]),
    )
    ec_2 = me.io.EntityCollection(
        x=[2000, 3000, 4000] * u.mm,
        Ms=me.Ms([22, 33, 44]),
    )
    ec_merged_1 = me.merge(ec_1, ec_2, on="x")
    ec_check_1 = me.io.EntityCollection(
        x=[2, 3] * u.m,
        Ms_x=me.Ms([2, 3]),
        Ms_y=me.Ms([22, 33]),
    )
    assert np.all(ec_merged_1.x == ec_check_1.x)
    assert ec_merged_1.Ms_x == ec_check_1.Ms_x
    assert ec_merged_1.Ms_y == ec_check_1.Ms_y

    ec_merged_2 = me.merge(ec_2, ec_1, on="x")
    ec_check_2 = me.io.EntityCollection(
        x=[2000, 3000] * u.mm,
        Ms_x=me.Ms([2, 3]),
        Ms_y=me.Ms([22, 33]),
    )
    assert np.all(ec_merged_2.x == ec_check_2.x)
    assert ec_merged_2.Ms_x == ec_check_2.Ms_x
    assert ec_merged_2.Ms_y == ec_check_2.Ms_y


def test_merge_left():
    """Test left merge function."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], y=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        y=[2, 3, 4],
        A=me.A([2, 3, 4]),
    )
    ec_merged_left = me.merge(ec_1, ec_2, on=["x", "y"], how="left")
    ec_check_left = me.io.EntityCollection(
        x=np.array([1, 2, 3]),
        y=np.array([1, 2, 3]),
        Ms=me.Ms([1, 2, 3]),
        A=me.A([np.nan, 2, 3]),
    )
    assert np.all(ec_merged_left.x == ec_check_left.x)
    assert np.all(ec_merged_left.y == ec_check_left.y)
    assert ec_merged_left.Ms == ec_check_left.Ms
    assert ec_merged_left.A == ec_check_left.A


def test_merge_right():
    """Test right merge function."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], y=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        y=[2, 3, 4],
        Ms=me.Ms([2, 3, 4]),
    )
    ec_merged_right = me.merge(ec_1, ec_2, on=["x", "y"], how="right")
    ec_check_right = me.io.EntityCollection(
        x=np.array([2, 3, 4]),
        y=np.array([2, 3, 4]),
        Ms=me.Ms([2, 3, np.nan]),
        A=me.A([2, 3, 4]),
    )
    assert np.all(ec_merged_right.x == ec_check_right.x)
    assert np.all(ec_merged_right.y == ec_check_right.y)
    assert ec_merged_right.Ms == ec_check_right.Ms
    assert ec_merged_right.A == ec_check_right.A


def test_merge_outer():
    """Test outer merge function."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], y=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        y=[2, 3, 4],
        Ms=me.Ms([2, 3, 4]),
    )
    ec_merged_outer = me.merge(ec_1, ec_2, on=["x", "y"], how="outer")
    ec_check_outer = me.io.EntityCollection(
        x=np.array([1, 2, 3, 4]),
        y=np.array([1, 2, 3, 4]),
        Ms_x=me.Ms([1, 2, 3, np.nan]),
        Ms_y=me.Ms([np.nan, 2, 3, 4]),
    )
    assert np.all(ec_merged_outer.x == ec_check_outer.x)
    assert ec_merged_outer.Ms == ec_check_outer.Ms


def test_merge_cross():
    """Test cross merge function."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], y=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        y=[2, 3, 4],
        Ms=me.Ms([2, 3, 4]),
    )
    with pytest.raises(ValueError):
        me.merge(ec_1, ec_2, on=["x", "y"], how="cross")
    ec_merged_cross = me.merge(ec_1, ec_2, how="cross")
    ec_check_cross = me.io.EntityCollection(
        x_x=np.array([1, 1, 1, 2, 2, 2, 3, 3, 3]),
        y_x=np.array([1, 1, 1, 2, 2, 2, 3, 3, 3]),
        Ms_x=me.Ms([1, 1, 1, 2, 2, 2, 3, 3, 3]),
        x_y=np.array([2, 2, 2, 3, 3, 3, 4, 4, 4]),
        y_y=np.array([2, 2, 2, 3, 3, 3, 4, 4, 4]),
        Ms_y=me.Ms([2, 2, 2, 3, 3, 3, 4, 4, 4]),
    )
    assert np.all(ec_merged_cross.x_x == ec_check_cross.x_x)
    assert np.all(ec_merged_cross.y_x == ec_check_cross.y_x)
    assert ec_merged_cross.Ms_x == ec_check_cross.Ms_x
    assert np.all(ec_merged_cross.x_y == ec_check_cross.x_y)
    assert np.all(ec_merged_cross.y_y == ec_check_cross.y_y)
    assert ec_merged_cross.Ms_y == ec_check_cross.Ms_y


def test_merge_different_names():
    """Test merge on different column names."""
    ec_1 = me.io.EntityCollection(x_array=[1, 2], y_array=[1, 2], Ms=me.Ms([100, 200]))
    ec_2 = me.io.EntityCollection(
        x=[1, 2],
        y=[1, 2],
        A=me.A([0.8, 0.8]),
    )
    ec_merged_1 = me.merge(
        ec_1, ec_2, left_on=["x_array", "y_array"], right_on=["x", "y"], how="inner"
    )
    ec_check_1 = me.io.EntityCollection(
        x=np.array([1, 2]),
        x_array=np.array([1, 2]),
        y=np.array([1, 2]),
        y_array=np.array([1, 2]),
        Ms=me.Ms([100, 200]),
        A=me.A([0.8, 0.8]),
    )
    assert np.all(ec_merged_1.x == ec_check_1.x)
    assert np.all(ec_merged_1.x_array == ec_check_1.x_array)
    assert np.all(ec_merged_1.y == ec_check_1.y)
    assert np.all(ec_merged_1.y_array == ec_check_1.y_array)
    assert ec_merged_1.Ms == ec_check_1.Ms
    assert ec_merged_1.A == ec_check_1.A


def test_merge_indicator():
    """Test merge with indicator=True."""
    ec_1 = me.io.EntityCollection(x=[1, 2, 3], y=[1, 2, 3], Ms=me.Ms([1, 2, 3]))
    ec_2 = me.io.EntityCollection(
        x=[2, 3, 4],
        y=[2, 3, 4],
        Ms=me.Ms([2, 3, 4]),
    )
    ec_merged = me.merge(ec_1, ec_2, on=["x", "y"], how="outer", indicator=True)
    ec_check = me.io.EntityCollection(
        x=np.array([1, 2, 3, 4]),
        y=np.array([1, 2, 3, 4]),
        Ms_x=me.Ms([1, 2, 3, np.nan]),
        Ms_y=me.Ms([np.nan, 2, 3, 4]),
        _merge=["left_only", "both", "both", "right_only"],
    )
    assert np.all(ec_merged.x == ec_check.x)
    assert np.all(ec_merged.y == ec_check.y)
    assert ec_merged.Ms_x == ec_check.Ms_x
    assert ec_merged.Ms_y == ec_check.Ms_y
    assert np.all(ec_merged._merge == ec_check._merge)
