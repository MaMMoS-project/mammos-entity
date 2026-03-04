from pathlib import Path

import h5py
import mammos_units as u
import pytest

import mammos_entity as me


def test_entity_to_hdf5_root():
    with h5py.File.in_memory() as f:
        T = me.T(100, "K")
        T.to_hdf5(f, "T")
        assert "T" in f
        assert f["T"][()] == T.value
        assert f["T"].attrs["unit"] == T.unit
        assert f["T"].attrs["ontology_label"] == T.ontology_label
        assert f["T"].attrs["ontology_iri"] == T.ontology.iri
        assert f["T"].attrs["mammos_entity_version"] == me.__version__
        assert me.from_hdf5(f["T"]) == T


def test_entity_to_hdf5_group():
    with h5py.File.in_memory() as f:
        Ms = me.Ms([[10, 20], [30, 40.0]], description="test")
        Ms.to_hdf5(f, "/base/Ms")
        assert "base" in f
        assert "Ms" in f["base"]
        assert (f["/base/Ms"][()] == Ms.value).all()
        assert f["/base/Ms"].attrs["description"] == Ms.description
        assert "mammos_entity_version" not in f["/base"].attrs
        assert f["/base/Ms"].attrs["mammos_entity_version"] == me.__version__
        assert me.from_hdf5(f["/base/Ms"]) == Ms


def test_entity_to_hdf5_existing_and_nested_groups():
    with h5py.File.in_memory() as f:
        Ms = me.Ms([[10, 20], [30, 40.0]], description="test")
        Ms.to_hdf5(f, "/base/Ms")
        Ms.to_hdf5(f["/base"], "Ms2")
        assert me.from_hdf5(f["/base/Ms2"]) == Ms

        Ms.to_hdf5(f["/base"], "sub/Ms")
        assert me.from_hdf5(f["/base/sub/Ms"]) == Ms


def test_entity_to_hdf5_overwrite_error():
    with h5py.File.in_memory() as f:
        Ms = me.Ms([[10, 20], [30, 40.0]], description="test")
        Ms.to_hdf5(f, "/base/Ms")

        with pytest.raises(ValueError, match="name already exists"):
            Ms.to_hdf5(f, "/base/Ms")


def test_entity_collection_to_hdf5_group():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )

        col.to_hdf5(f, "/sample1/properties")
        assert f["/sample1/properties"].attrs["description"] == col.description
        assert f["/sample1/properties"].attrs["mammos_entity_version"] == me.__version__
        assert "mammos_entity_version" not in f["/sample1"].attrs
        assert "mammos_entity_version" not in f["/sample1/properties/Ms"].attrs
        assert "mammos_entity_version" not in f["/sample1/properties/T"].attrs
        assert "mammos_entity_version" not in f["/sample1/properties/Tc"].attrs
        assert list(f["/sample1/properties"]) == ["Ms", "T", "Tc"]


def test_entity_collection_to_hdf5_roundtrip():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )
        col.to_hdf5(f, "/sample1/properties")

        col_read = me.from_hdf5(f["/sample1/properties"])
        assert isinstance(col_read, me.EntityCollection)
        assert col_read.description == col.description
        assert [name for name, _entity in col_read] == ["Ms", "T", "Tc"]
        assert col_read.Ms == col.Ms
        assert col_read.T == col.T
        assert col_read.Tc == col.Tc


def test_entity_collection_to_hdf5_extra_features_do_not_affect_read():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )
        group = col.to_hdf5(f, "/sample1/properties")

        group["Ms"].dims[0].label = "T"
        group["T"].make_scale("T")
        group["Ms"].dims[0].attach_scale(group["T"])
        assert group["Ms"].dims[0]["T"] == group["T"]

        col_read = me.from_hdf5(f["/sample1/properties"])
        assert col_read.Ms == col.Ms
        assert col_read.T == col.T


def test_nested_entity_collection_to_hdf5_roundtrip():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )
        sample = me.EntityCollection(
            description="produced by student",
            properties=col,
            edge_length=[1, 2, 3] * u.mm,
            measurement_device="device X",
        )
        sample.to_hdf5(f, "sample1")

        sample_read = me.from_hdf5(f["sample1"])
        assert isinstance(sample_read, me.EntityCollection)
        assert "properties" in sample_read
        assert "edge_length" in sample_read
        assert "measurement_device" in sample_read

        assert isinstance(sample_read.properties, me.EntityCollection)
        assert isinstance(sample_read.properties.Ms, me.Entity)
        assert isinstance(sample_read.edge_length, u.Quantity)
        assert isinstance(sample_read.measurement_device, str)

        assert me.from_hdf5(
            f["sample1/measurement_device"], decode_bytes=False
        ) == sample.measurement_device.encode("utf8")


def test_nested_entity_collection_to_hdf5_full_file_read():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )
        sample = me.EntityCollection(
            description="produced by student",
            properties=col,
            edge_length=[1, 2, 3] * u.mm,
            measurement_device="device X",
        )
        sample.to_hdf5(f, "sample1")

        full_content = me.from_hdf5(f)
        assert isinstance(full_content, me.EntityCollection)
        assert full_content.description == ""
        assert isinstance(full_content.sample1, me.EntityCollection)
        assert full_content.sample1.description == sample.description
        assert full_content.sample1.properties.Tc.value == 600


def test_nested_entity_collection_to_hdf5_version_propagation():
    with h5py.File.in_memory() as f:
        col = me.EntityCollection(
            description="intrinsic properties",
            Ms=me.Ms([300, 250, 200], "kA/m"),
            T=me.T([50, 100, 200]),
            Tc=me.Tc(600, "K"),
        )
        sample = me.EntityCollection(
            description="produced by student",
            properties=col,
            edge_length=[1, 2, 3] * u.mm,
            measurement_device="device X",
        )
        sample.to_hdf5(f, "sample1")

        col.to_hdf5(f, "sample1/extra")
        me.A().to_hdf5(f, "sample1/a")
        me.A().to_hdf5(f, "sample1/extra/a")

        assert f["/sample1"].attrs["mammos_entity_version"] == me.__version__
        assert "mammos_entity_version" not in f["/sample1/properties"].attrs

        assert f["/sample1/extra"].attrs["mammos_entity_version"] == me.__version__
        assert "mammos_entity_version" not in f["/sample1/extra/Ms"].attrs
        assert "mammos_entity_version" not in f["/sample1/extra/T"].attrs
        assert "mammos_entity_version" not in f["/sample1/extra/Tc"].attrs
        assert f["/sample1/a"].attrs["mammos_entity_version"] == me.__version__
        assert f["/sample1/extra/a"].attrs["mammos_entity_version"] == me.__version__


def test_to_new_hdf5_file_entity(tmp_path: Path):
    filename = tmp_path / "test.h5"
    T = me.T()
    T.to_hdf5(filename, "entity")

    assert filename.is_file()

    content = me.from_hdf5(filename)
    assert isinstance(content, me.EntityCollection)
    assert content.entity == T


def test_to_new_hdf5_file_overwrite_collection(tmp_path: Path):
    # First write an entity to the file
    filename = tmp_path / "test.h5"
    T = me.T()
    T.to_hdf5(filename, "entity")

    # Then overwrite the same file with a collection
    c = me.EntityCollection(Tc=me.Tc(), Ms=me.Ms(), description="abc")
    c.to_hdf5(str(filename))

    content = me.from_hdf5(str(filename))
    assert isinstance(content, me.EntityCollection)
    assert content.description == "abc"
    # We do not create a new group here; h5py's default behavior does not track
    # insertion order, so the names appear as ["Ms", "Tc"] even though the
    # EntityCollection was created with Tc before Ms. This changes when we create
    # a group manually (see the next test), where insertion order is tracked.
    assert [name for name, _ in content] == ["Ms", "Tc"]
    assert content.Ms == me.Ms()
    assert content.Tc == me.Tc()


def test_to_new_hdf5_file_ordered_group(tmp_path: Path):
    filename = tmp_path / "test_ordered.h5"
    c = me.EntityCollection(Tc=me.Tc(), Ms=me.Ms(), description="abc")
    c.to_hdf5(str(filename), "ordered")

    content = me.from_hdf5(str(filename))
    assert [name for name, _ in content.ordered] == ["Tc", "Ms"]
