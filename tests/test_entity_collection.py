import pandas as pd
import pytest

import mammos_entity as me


def test_entity_collection_with_description():
    """Check that the description of an EntityCollection is well defined."""
    ec = me.EntityCollection(
        "Magnetization on a grid.", x=[0, 0, 1, 1], y=[0, 1, 0, 1], M=me.M([1, 2, 3, 4])
    )
    assert ec.description == "Magnetization on a grid."
    assert [name for name, _entity in ec] == ["x", "y", "M"]

    ec.T = me.T(2)
    assert [name for name, _entity in ec] == ["x", "y", "M", "T"]

    # changing class elements does not change the entities
    ec.description = "A new description"
    assert [name for name, _entity in ec] == ["x", "y", "M", "T"]
    assert ec.description == "A new description"
    del ec.T
    assert [name for name, _entity in ec] == ["x", "y", "M"]


def test_entity_name_clash():
    ec = me.EntityCollection(to_dataframe=me.Ms())
    assert [name for name, _entity in ec] == ["to_dataframe"]
    assert callable(ec.to_dataframe)
    assert ec["to_dataframe"] == me.Ms()

    ec.to_dataframe = "missing"
    assert [name for name, _entity in ec] == ["to_dataframe"]
    assert ec.to_dataframe == "missing"
    assert ec["to_dataframe"] == me.Ms()

    with pytest.raises(KeyError):
        ec["description"] = me.T()


def test_add_remove_entities():
    ec = me.EntityCollection()
    assert [name for name, _entity in ec] == []

    ec.Ms = me.Ms()
    ec.A = me.A()
    ec["T center"] = me.T()

    assert [name for name, _entity in ec] == ["Ms", "A", "T center"]

    assert ec["Ms"] == me.Ms()
    assert ec.A == me.A()  # noqa: SIM300  # ruff wants to swap left-right
    assert ec["T center"] == me.T()

    del ec.Ms
    del ec["A"]
    assert [name for name, _entity in ec] == ["T center"]

    del ec["T center"]
    assert [name for name, _entity in ec] == []


def test_iter():
    Ms = me.Ms([1, 2, 3])
    T = me.T(100)
    ec = me.EntityCollection(Ms=Ms, T=T)

    assert list(ec) == [("Ms", Ms), ("T", T)]


def test_contains():
    ec = me.EntityCollection(Ms=me.Ms())

    assert "Ms" in ec
    assert "Js" not in ec

    # checks only for entities, nothing else
    assert "description" not in ec
    assert "to_dataframe" not in ec


def test_dir():
    ec = me.EntityCollection(Ms=me.Ms())
    ec["T center"] = me.T()

    assert "Ms" in dir(ec)
    assert "T center" in dir(ec)


def test_bad_description():
    """Check bad type for description of an EntityCollection."""
    with pytest.raises(ValueError):
        me.EntityCollection(description=1)


def test_to_dataframe():
    """Check that the conversion to DataFrame works as intended."""
    ec = me.EntityCollection(
        "Magnetization on a grid.",
        x=[0, 0, 1, 1],
        M=me.M([1, 2, 3, 4]),
        T=me.T([100, 200, 300, 400], "mK"),
    )
    df = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "M": [1.0, 2.0, 3.0, 4.0],
            "T": [100.0, 200.0, 300.0, 400.0],
        }
    )
    assert df.equals(ec.to_dataframe())
    df_with_units = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "M (A / m)": [1.0, 2.0, 3.0, 4.0],
            "T (mK)": [100.0, 200.0, 300.0, 400.0],
        }
    )
    assert df_with_units.equals(ec.to_dataframe(include_units=True))
