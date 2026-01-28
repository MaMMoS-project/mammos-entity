import pandas as pd
import pytest

import mammos_entity as me


def test_EntityCollection_with_description():
    """Check that the description of an EntityCollection is well defined."""
    ec = me.EntityCollection(
        "Magnetization on a grid.", x=[0, 0, 1, 1], y=[0, 1, 0, 1], M=me.M([1, 2, 3, 4])
    )
    assert ec.description == "Magnetization on a grid."
    assert list(ec.entities.keys()) == ["x", "y", "M"]

    ec.T = me.T(2)
    assert list(ec.entities.keys()) == ["x", "y", "M", "T"]

    # changing class elements does not change the entities
    ec.description = "A new description"
    assert list(ec.entities.keys()) == ["x", "y", "M", "T"]
    assert ec.description == "A new description"
    del ec.T
    assert list(ec.entities.keys()) == ["x", "y", "M"]


def test_EntityCollection_name_clash():
    ec = me.io.EntityCollection(to_dataframe="value")
    assert list(ec.entities.keys()) == ["to_dataframe"]
    assert callable(ec.to_dataframe)
    assert ec.entities["to_dataframe"] == "value"

    ec.to_dataframe = "missing"
    assert list(ec.entities.keys()) == ["to_dataframe"]
    assert ec.to_dataframe == "missing"
    assert ec.entities["to_dataframe"] == "value"


def test_EntityCollection_bad_description():
    """Check bad type for description of an EntityCollection."""
    with pytest.raises(ValueError):
        me.EntityCollection(description=1)


def test_EntityCollection_dataframe():
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
