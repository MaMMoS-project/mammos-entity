from pathlib import Path

import h5py
import mammos_units as u
import pytest

import mammos_entity as me


def test_entity_to_hdf5():
    f = h5py.File.in_memory()

    # write to dataset
    T = me.T(100, "K")
    T.to_hdf5(f, "T")
    assert "T" in f
    assert f["T"][()] == T.value
    assert f["T"].attrs["unit"] == T.unit
    assert f["T"].attrs["ontology_label"] == T.ontology_label
    assert f["T"].attrs["ontology_iri"] == T.ontology.iri
    assert f["T"].attrs["mammos_entity_version"] == me.__version__
    assert me.from_hdf5(f["T"]) == T

    # write to dataset in newly created group
    Ms = me.Ms([[10, 20], [30, 40.0]], description="test")
    Ms.to_hdf5(f, "/base/Ms")
    assert "base" in f
    assert "Ms" in f["base"]
    assert (f["/base/Ms"][()] == Ms.value).all()
    assert f["/base/Ms"].attrs["description"] == Ms.description
    assert "mammos_entity_version" not in f["/base"].attrs
    assert f["/base/Ms"].attrs["mammos_entity_version"] == me.__version__
    assert me.from_hdf5(f["/base/Ms"]) == Ms

    # write to existing group
    Ms.to_hdf5(f["/base"], "Ms2")
    assert me.from_hdf5(f["/base/Ms2"]) == Ms

    # write to newly created subgroup inside existing group
    Ms.to_hdf5(f["/base"], "sub/Ms")
    assert me.from_hdf5(f["/base/sub/Ms"]) == Ms

    with pytest.raises(ValueError, match="name already exists"):
        Ms.to_hdf5(f, "/base/Ms")

    f.close()


def test_entity_collection_to_hdf5():
    f = h5py.File.in_memory()

    col = me.EntityCollection(
        description="intrinsic properties",
        Ms=me.Ms([300, 250, 200], "kA/m"),
        T=me.T([50, 100, 200]),
        Tc=me.Tc(600, "K"),
    )

    # write group and create base group on the fly
    group = col.to_hdf5(f, "/sample1/properties")
    assert f["/sample1/properties"].attrs["description"] == col.description
    assert f["/sample1/properties"].attrs["mammos_entity_version"] == me.__version__
    assert "mammos_entity_version" not in f["/sample1"].attrs
    assert "mammos_entity_version" not in f["/sample1/properties/Ms"].attrs
    assert "mammos_entity_version" not in f["/sample1/properties/T"].attrs
    assert "mammos_entity_version" not in f["/sample1/properties/Tc"].attrs
    assert list(f["/sample1/properties"]) == ["Ms", "T", "Tc"]

    col_read = me.from_hdf5(f["/sample1/properties"])
    assert isinstance(col_read, me.EntityCollection)
    assert col_read.description == col.description
    assert [name for name, _entity in col_read] == ["Ms", "T", "Tc"]
    assert col_read.Ms == col.Ms
    assert col_read.T == col.T
    assert col_read.Tc == col.Tc

    # users have full control over additional hdf5 features
    group["Ms"].dims[0].label = "T"
    group["T"].make_scale("T")
    group["Ms"].dims[0].attach_scale(group["T"])
    assert group["Ms"].dims[0]["T"] == group["T"]
    # this does not affect reading (but the additional information is lost)
    col_read = me.from_hdf5(f["/sample1/properties"])
    assert col_read.Ms == col.Ms
    assert col_read.T == col.T

    f.close()


def test_nested_entity_collection_to_hdf5():
    f = h5py.File.in_memory()

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

    # write two nested collections using both api options
    sample.to_hdf5(f, "sample1")

    assert f["/sample1"].attrs["mammos_entity_version"] == me.__version__
    assert "mammos_entity_version" not in f["/sample1/properties"].attrs
    assert "mammos_entity_version" not in f["/sample1/properties/Ms"].attrs

    sample_read = me.from_hdf5(f["sample1"])
    assert "properties" in sample_read
    assert "edge_length" in sample_read
    assert "measurement_device" in sample_read

    assert me.from_hdf5(
        f["sample1/measurement_device"], decode_bytes=False
    ) == sample.measurement_device.encode("utf8")

    # we can also read the whole file and get one extra level of nesting
    full_content = me.from_hdf5(f)

    assert isinstance(full_content, me.EntityCollection)
    assert full_content.description == ""
    assert full_content.sample1.description == sample.description

    # we can access everything via the nesting
    assert full_content.sample1.properties.Tc.value == 600

    # add additional inner collection/entities to sample1 to test mammos_entity_version
    # propagation
    col.to_hdf5(f, "sample1/extra")
    me.A().to_hdf5(f, "sample1/a")
    me.A().to_hdf5(f, "sample1/extra/a")

    assert f["/sample1/extra"].attrs["mammos_entity_version"] == me.__version__
    assert "mammos_entity_version" not in f["/sample1/extra/Ms"].attrs
    assert "mammos_entity_version" not in f["/sample1/extra/T"].attrs
    assert "mammos_entity_version" not in f["/sample1/extra/Tc"].attrs
    assert f["/sample1/a"].attrs["mammos_entity_version"] == me.__version__
    assert f["/sample1/extra/a"].attrs["mammos_entity_version"] == me.__version__

    f.close()


def test_to_new_hdf5_file(tmp_path: Path):
    T = me.T()
    T.to_hdf5(tmp_path / "test.h5", "entity")

    assert (tmp_path / "test.h5").is_file()

    content = me.from_hdf5(tmp_path / "test.h5")
    assert isinstance(content, me.EntityCollection)
    assert content.entity == T

    # overwrite with a collection
    c = me.EntityCollection(Tc=me.Tc(), Ms=me.Ms(), description="abc")
    c.to_hdf5(str(tmp_path / "test.h5"))

    content2 = me.from_hdf5(str(tmp_path / "test.h5"))

    assert isinstance(content2, me.EntityCollection)
    assert content2.description == "abc"
    # Note for the following check: we do not create a new group and therefor, insertion
    # order is irrelevant (h5py by default does not track insertion order). This changes
    # when we create a group manually, where insertion order is tracked
    assert [name for name, _ in content2] == ["Ms", "Tc"]
    assert content2.Ms == me.Ms()
    assert content2.Tc == me.Tc()

    c.to_hdf5(str(tmp_path / "test.h5"), "ordered")
    content3 = me.from_hdf5(str(tmp_path / "test.h5"))
    assert [name for name, _ in content3.ordered] == ["Tc", "Ms"]
