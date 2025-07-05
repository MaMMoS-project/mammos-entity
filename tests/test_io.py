import mammos_units as u
import pytest

import mammos_entity as me
from mammos_entity.io import EntityCollection, entities_from_csv, entities_to_csv


def test_to_csv_no_data():
    with pytest.raises(RuntimeError):
        entities_to_csv("test.csv")


def test_different_types_column():
    with pytest.raises(TypeError):
        entities_to_csv("test.csv", data=[1, me.A()])


def test_scalar_column(tmp_path):
    entities_to_csv(tmp_path / "test.csv", A=me.A(1), Ms=me.Ms(2), K=me.Ku(3))

    read_csv = entities_from_csv(tmp_path / "test.csv")
    assert me.A(1) == read_csv.A
    assert me.M(2) == read_csv.Ms
    assert me.Ku(3) == read_csv.K


def test_read_collection_type(tmp_path):
    entities_to_csv(tmp_path / "simple.csv", data=[1, 2, 3])
    read_csv = entities_from_csv(tmp_path / "simple.csv")
    assert isinstance(read_csv, EntityCollection)


def test_read_write_csv(tmp_path):
    Ms = me.Ms([1e6, 2e6, 3e6])
    T = me.T([1, 2, 3])
    theta_angle = [0, 0.5, 0.7] * u.rad
    demag_factor = me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3])
    comments = ["Some comment", "Some other comment", "A third comment"]
    entities_to_csv(
        tmp_path / "example.csv",
        Ms=Ms,
        T=T,
        angle=theta_angle,
        n=demag_factor,
        comment=comments,
    )

    read_csv = entities_from_csv(tmp_path / "example.csv")

    assert read_csv.Ms == Ms
    assert read_csv.T == T
    assert all(read_csv.angle == theta_angle)
    assert read_csv.n == demag_factor
    assert all(read_csv.comment == comments)
