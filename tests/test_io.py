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
    # not supported for yaml because it cannot represent class Entity in the list
    with pytest.raises(TypeError):
        entities_to_file("test.csv", data=[1, me.A()])


@pytest.mark.parametrize("extension", ["csv", "yaml", "yml"])
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
def test_scalar_column(tmp_path, data, extension):
    entities_to_file(tmp_path / f"test.{extension}", **data)

    read_data = entities_from_file(tmp_path / f"test.{extension}")

    assert data["A"] == read_data.A
    assert data["Ms"] == read_data.Ms
    assert data["Ku"] == read_data.Ku


def test_EntityCollection_with_description():
    """Check that the description of an EntityCollection is well defined."""
    ec = me.io.EntityCollection(
        "Magnetization on a grid.", x=[0, 0, 1, 1], y=[0, 1, 0, 1], M=me.M([1, 2, 3, 4])
    )
    assert ec.description == "Magnetization on a grid."
    assert list(ec._elements_dictionary.keys()) == ["x", "y", "M"]


def test_EntityCollection_bad_description():
    """Check bad type for description of an EntityCollection."""
    with pytest.raises(ValueError):
        me.io.EntityCollection(description=1)


def test_EntityCollection_dataframe():
    """Check that the conversion to DataFrame works as intended."""
    ec = me.io.EntityCollection(
        "Magnetization on a grid.",
        x=[0, 0, 1, 1],
        M=me.M([1, 2, 3, 4]),
        T=me.T([100, 200, 300, 400], "mK"),
    )
    df = pd.DataFrame(
        {
            "x": [0, 0, 1, 1],
            "M (A / m)": [1.0, 2.0, 3.0, 4.0],
            "T (mK)": [100.0, 200.0, 300.0, 400.0],
        }
    )
    assert df.equals(ec.to_dataframe())


@pytest.mark.parametrize("extension", ["csv", "yaml", "yml"])
def test_read_collection_type(tmp_path, extension):
    entities_to_file(tmp_path / f"simple.{extension}", data=[1, 2, 3])
    read_data = entities_from_file(tmp_path / f"simple.{extension}")
    assert isinstance(read_data, EntityCollection)
    assert np.allclose(read_data.data, [1, 2, 3])


@pytest.mark.parametrize("extension", ["csv", "yaml", "yml"])
def test_write_read(tmp_path, extension):
    Ms = me.Ms([1e6, 2e6, 3e6])
    T = me.T([1, 2, 3])
    theta_angle = [0, 0.5, 0.7] * u.rad
    demag_factor = me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3])
    comments = ["Some comment", "Some other comment", "A third comment"]
    entities_to_file(
        tmp_path / f"example.{extension}",
        Ms=Ms,
        T=T,
        angle=theta_angle,
        n=demag_factor,
        comment=comments,
    )

    read_data = entities_from_file(tmp_path / f"example.{extension}")

    assert read_data.Ms == Ms
    assert read_data.T == T
    # Floating-point comparisons with == should ensure that we do not loose precision
    # when writing the data to file.
    assert all(read_data.angle == theta_angle)
    assert read_data.n == demag_factor
    assert list(read_data.comment) == comments

    df_with_units = read_data.to_dataframe()
    assert list(df_with_units.columns) == [
        "Ms (A / m)",
        "T (K)",
        "angle (rad)",
        "n",
        "comment",
    ]

    df_without_units = read_data.to_dataframe(include_units=False)
    assert list(df_without_units.columns) == ["Ms", "T", "angle", "n", "comment"]

    if extension == "csv":
        df = pd.read_csv(tmp_path / "example.csv", comment="#")

        assert all(df == df_without_units)


def test_write_read_yaml_multi_shape(tmp_path):
    T = me.T([1, 2, 3])
    Tc = me.Tc(100)
    multi_index = [[1, 2], [3, 4]]

    entities_to_file(
        tmp_path / "example.yaml",
        T=T,
        Tc=Tc,
        multi_index=multi_index,
    )

    read_data = entities_from_file(tmp_path / "example.yaml")

    assert read_data.T == T
    assert read_data.Tc == Tc
    assert read_data.multi_index == multi_index

    with pytest.raises(ValueError):
        read_data.to_dataframe()


def test_wrong_file_version_csv(tmp_path):
    file_content = textwrap.dedent(
        """\
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


def test_no_mixed_shape_in_csv():
    with pytest.raises(ValueError):
        me.io.entities_to_file(
            "will-not-be-written.csv",
            T=me.T([1, 2, 3]),
            Tc=me.Tc(100),
        )


def test_no_multi_dim_in_csv():
    with pytest.raises(ValueError):
        me.io.entities_to_file(
            "will-not-be-written.csv",
            T=me.T([[1, 2, 3]]),
        )


def test_wrong_file_version_yaml(tmp_path):
    file_content = textwrap.dedent(
        """
        metadata:
          version: v0
        data:
          index:
            ontology_label: null
            ontology_iri: null
            unit: null
            value: [1, 2]
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    with pytest.raises(RuntimeError):
        me.io.entities_from_file(tmp_path / "data.yaml")


@pytest.mark.parametrize("extension", ["csv", "yaml", "yml"])
def test_empty_file(tmp_path, extension):
    (tmp_path / f"data.{extension}").touch()
    with pytest.raises(RuntimeError):
        me.io.entities_from_file(tmp_path / f"data.{extension}")


def test_no_data_yaml(tmp_path):
    file_content = textwrap.dedent(
        """
        metadata:
          version: v1
        data:
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    with pytest.raises(RuntimeError):
        me.io.entities_from_file(tmp_path / "data.yaml")


@pytest.mark.parametrize("extension", ["csv", "yaml", "yml"])
def test_wrong_iri(tmp_path, extension: str):
    filename = tmp_path / f"example.{extension}"
    me.io.entities_to_file(filename, Ms=me.Ms())

    # check that the file is correct
    assert me.io.entities_from_file(filename).Ms == me.Ms()

    # break IRI in file
    with open(filename, "r+") as f:
        data = f.read()
        data = data.replace("w3id.org/emmo", "example.com/my_ontology")
        f.seek(0)
        f.write(data)

    with pytest.raises(RuntimeError, match="Incompatible IRI for Entity"):
        me.io.entities_from_file(filename)
