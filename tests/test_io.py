import textwrap

import mammos_units as u
import numpy as np
import pandas as pd
import pytest

import mammos_entity as me
from mammos_entity.io import EntityCollection, entities_from_file, entities_to_file


def test_to_csv_no_data():
    with pytest.raises(RuntimeError):
        entities_to_file("test.csv")


@pytest.mark.skip(reason="Allow multiple datatypes in one column for now.")
def test_different_types_column():
    with pytest.raises(TypeError):
        entities_to_file("test.csv", data=[1, me.A()])


@pytest.mark.parametrize(
    "data",
    [
        {"A": 1.0, "Ms": 2.0, "Ku": 3.0},
        {
            "A": 1.0 * (u.J / u.m),
            "Ms": 2 * (u.A / u.m),
            "Ku": 3 * (u.J / u.m**3),
        },
        {"A": me.A(1), "Ms": me.Ms(2), "Ku": me.Ku(3)},
    ],
    ids=["floats", "quantites", "entities"],
)
def test_scalar_column(tmp_path, data):
    entities_to_file(tmp_path / "test.csv", **data)

    read_csv = entities_from_file(tmp_path / "test.csv")

    assert data["A"] == read_csv.A
    assert data["Ms"] == read_csv.Ms
    assert data["Ku"] == read_csv.Ku


def test_read_collection_type(tmp_path):
    entities_to_file(tmp_path / "simple.csv", data=[1, 2, 3])
    read_csv = entities_from_file(tmp_path / "simple.csv")
    assert isinstance(read_csv, EntityCollection)
    assert np.allclose(read_csv.data, [1, 2, 3])


def test_read_write_csv(tmp_path):
    Ms = me.Ms([1e6, 2e6, 3e6])
    T = me.T([1, 2, 3])
    theta_angle = [0, 0.5, 0.7] * u.rad
    demag_factor = me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3])
    comments = ["Some comment", "Some other comment", "A third comment"]
    entities_to_file(
        tmp_path / "example.csv",
        Ms=Ms,
        T=T,
        angle=theta_angle,
        n=demag_factor,
        comment=comments,
    )

    read_csv = entities_from_file(tmp_path / "example.csv")

    assert read_csv.Ms == Ms
    assert read_csv.T == T
    # Floating-point comparisons with == should ensure that we do not loose precision
    # when writing the data to file.
    assert all(read_csv.angle == theta_angle)
    assert read_csv.n == demag_factor
    assert all(read_csv.comment == comments)

    df_with_units = read_csv.to_dataframe()
    assert list(df_with_units.columns) == [
        "Ms (A / m)",
        "T (K)",
        "angle (rad)",
        "n",
        "comment",
    ]

    df_without_units = read_csv.to_dataframe(include_units=False)
    assert list(df_without_units.columns) == ["Ms", "T", "angle", "n", "comment"]

    df = pd.read_csv(tmp_path / "example.csv", comment="#")

    assert all(df == df_without_units)


def test_wrong_file_version(tmp_path):
    file_content = textwrap.dedent(
        """
        #mammos csv v0
        #
        #
        #
        index
        1
        2
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(RuntimeError):
        me.io.entities_from_file(tmp_path / "data.csv")
