import os
import textwrap
from pathlib import Path

import h5py
import mammos_units as u
import pandas as pd
import pytest

import mammos_entity as me

# @pytest.mark.skip(reason="Allow multiple datatypes in one column for now.")
# def test_different_types_column():
#     # not supported for yaml because it cannot represent class Entity in the list
#     with pytest.raises(TypeError):
#         entities_to_file("test.csv", data=[1, me.A()])


def test_scalar_column_csv(tmp_path):
    data = me.EntityCollection(A=1.0, Ms=2 * u.A / u.m, Ku=me.Ku(3))
    data.to_csv(tmp_path / "test.csv")

    read_data = me.from_csv(tmp_path / "test.csv")

    assert data["A"] == read_data.A
    assert data["Ms"] == read_data.Ms
    assert data["Ku"] == read_data.Ku


def test_scalar_column_yaml(tmp_path):
    data = me.EntityCollection(A=1.0, Ms=2 * u.A / u.m, Ku=me.Ku(3))
    data.to_yaml(tmp_path / "test.yaml")

    read_data = me.from_yaml(tmp_path / "test.yaml")

    assert data["A"] == read_data.A
    assert data["Ms"] == read_data.Ms
    assert data["Ku"] == read_data.Ku


def test_write_read_csv(tmp_path):
    collection = me.EntityCollection(
        description="Test file description.\nTest second line.",
        Ms=me.Ms([1e6, 2e6, 3e6], description="evaluated\nexperimentally"),
        T=me.T([1, 2, 3], description="description, with comma"),
        theta_angle=[0, 0.5, 0.7] * u.rad,
        demag_factor=me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]),
        comments=["Some comment", "Some other comment", "A third comment"],
    )
    collection["the length"] = me.Entity("Length", [1, 2, 3])
    collection.to_csv(tmp_path / "example.csv")

    read_data = me.from_csv(tmp_path / "example.csv")

    assert isinstance(read_data, me.EntityCollection)
    assert read_data.description == collection.description
    assert read_data.Ms == collection.Ms
    assert read_data.Ms.description == collection.Ms.description
    assert read_data.T == collection.T
    assert read_data.T.description == collection.T.description
    # Floating-point comparisons with == should ensure that we do not loose precision
    # when writing the data to file.
    assert all(read_data.theta_angle == collection.theta_angle)
    assert read_data.demag_factor == collection.demag_factor
    assert list(read_data.comments) == collection.comments
    assert read_data["the length"] == collection["the length"]

    df_without_units = read_data.to_dataframe()
    assert list(df_without_units.columns) == [
        "Ms",
        "T",
        "theta_angle",
        "demag_factor",
        "comments",
        "the length",
    ]

    df_with_units = read_data.to_dataframe(include_units=True)
    assert list(df_with_units.columns) == [
        "Ms (A / m)",
        "T (K)",
        "theta_angle (rad)",
        "demag_factor",
        "comments",
        "the length (m)",
    ]

    df = pd.read_csv(tmp_path / "example.csv", header=9)
    assert all(df == df_without_units)


def test_write_read_yaml(tmp_path):
    collection = me.EntityCollection(
        description="Test file description.\nTest second line.",
        Ms=me.Ms([1e6, 2e6, 3e6], description="evaluated\nexperimentally"),
        T=me.T([1, 2, 3], description="description, with comma"),
        theta_angle=[0, 0.5, 0.7] * u.rad,
        demag_factor=me.Entity("DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]),
        comments=["Some comment", "Some other comment", "A third comment"],
    )
    collection["the length"] = me.Entity("Length", [1, 2, 3])
    collection.to_yaml(tmp_path / "example.yaml")

    read_data = me.from_yaml(tmp_path / "example.yaml")

    assert isinstance(read_data, me.EntityCollection)
    assert read_data.description == collection.description
    assert read_data.Ms == collection.Ms
    assert read_data.Ms.description == collection.Ms.description
    assert read_data.T == collection.T
    assert read_data.T.description == collection.T.description
    # Floating-point comparisons with == should ensure that we do not loose precision
    # when writing the data to file.
    assert all(read_data.theta_angle == collection.theta_angle)
    assert read_data.demag_factor == collection.demag_factor
    assert list(read_data.comments) == collection.comments
    assert read_data["the length"] == collection["the length"]


def test_read_csv_v1(tmp_path):
    file_content = textwrap.dedent(
        """\
        #mammos csv v1
        #SpontaneousMagnetization,ThermodynamicTemperature,,DemagnetizingFactor,
        #https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f,,https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
        #kA / m,K,rad,,
        Ms,T,angle,demag_factor,comment
        600.0,1.0,0.0,0.3333333333333333,Some comment
        650.0,2.0,0.5,0.3333333333333333,Some other comment
        700.0,3.0,0.7,0.3333333333333333,A third comment
        """
    )
    (tmp_path / "data.csv").write_text(file_content)
    read_data = me.from_csv(tmp_path / "data.csv")
    assert read_data.description == ""
    assert read_data.Ms == me.Ms([600, 650, 700], "kA/m")
    assert me.T([1, 2, 3]) == read_data.T
    assert all(read_data.angle == [0, 0.5, 0.7] * u.rad)
    assert read_data.demag_factor == me.Entity(
        "DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]
    )
    assert list(read_data.comment) == [
        "Some comment",
        "Some other comment",
        "A third comment",
    ]


def test_read_csv_v2(tmp_path):
    file_content = textwrap.dedent(
        """\
        #mammos csv v2
        #----------------------------------------
        # File description.
        #----------------------------------------
        #SpontaneousMagnetization,ThermodynamicTemperature,,DemagnetizingFactor,
        #https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f,,https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e,
        #kA / m,K,rad,,
        Ms,T,angle,demag_factor,comment
        600.0,1.0,0.0,0.3333333333333333,Some comment
        650.0,2.0,0.5,0.3333333333333333,Some other comment
        700.0,3.0,0.7,0.3333333333333333,A third comment
        """
    )
    (tmp_path / "data.csv").write_text(file_content)
    read_data = me.from_csv(tmp_path / "data.csv")

    assert read_data.description == "File description."
    assert read_data.Ms == me.Ms([600, 650, 700], "kA/m")
    assert me.T([1, 2, 3]) == read_data.T
    assert all(read_data.angle == [0, 0.5, 0.7] * u.rad)
    assert read_data.demag_factor == me.Entity(
        "DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]
    )
    assert list(read_data.comment) == [
        "Some comment",
        "Some other comment",
        "A third comment",
    ]


def test_read_csv_v3(tmp_path):
    # hack: trick every platform to save the two-line description using `\n`
    file_content = (
        textwrap.dedent(
            """\
        # mammos csv v3
        #----------------------------------------
        # Test file description.
        # Test 1, 2, 3.
        #----------------------------------------
        SpontaneousMagnetization,ThermodynamicTemperature,,
        "first line{description_newline}second line","description, with a comma",,
        https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f,,
        kA / m,K,rad,
        Ms,T,angle,comment
        600.0,1.0,0.0,Some comment
        650.0,2.0,0.5,Some other comment
        700.0,3.0,0.7,A third comment
        """
        )
        .replace("\n", os.linesep)
        .format(description_newline="\n")
    )
    (tmp_path / "data.csv").write_text(file_content, newline="")
    read_data = me.from_csv(tmp_path / "data.csv")

    assert read_data.description == "Test file description.\nTest 1, 2, 3."
    assert read_data.Ms == me.Ms([600, 650, 700], "kA/m")
    assert read_data.Ms.description == "first line\nsecond line"
    assert me.T([1, 2, 3]) == read_data.T
    assert read_data.T.description == "description, with a comma"
    assert all(read_data.angle == [0, 0.5, 0.7] * u.rad)
    assert list(read_data.comment) == [
        "Some comment",
        "Some other comment",
        "A third comment",
    ]


def test_read_yaml_v1(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v1
          description: null
        data:
          Ms:
            ontology_label: SpontaneousMagnetization
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
            unit: kA / m
            value: [600.0, 650.0, 700.0]
          T:
            ontology_label: ThermodynamicTemperature
            ontology_iri: https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f
            unit: K
            value: [1.0, 2.0, 3.0]
          angle:
            ontology_label: null
            ontology_iri: null
            unit: rad
            value: [0.0, 0.5, 0.7]
          demag_factor:
            ontology_label: DemagnetizingFactor
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
            unit: ''
            value: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333]
          comment:
            ontology_label: null
            ontology_iri: null
            unit: null
            value: [Some comment, Some other comment, A third comment]
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    read_data = me.from_yaml(tmp_path / "data.yaml")

    assert read_data.description == ""
    assert read_data.Ms == me.Ms([600, 650, 700], "kA/m")
    assert me.T([1, 2, 3]) == read_data.T
    assert all(read_data.angle == [0, 0.5, 0.7] * u.rad)
    assert read_data.demag_factor == me.Entity(
        "DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]
    )
    assert list(read_data.comment) == [
        "Some comment",
        "Some other comment",
        "A third comment",
    ]


def test_read_yaml_v2(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
          description: |-
            File description.
        data:
          Ms:
            ontology_label: SpontaneousMagnetization
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
            unit: kA / m
            value: [600.0, 650.0, 700.0]
            description: ''
          T:
            ontology_label: ThermodynamicTemperature
            ontology_iri: https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f
            unit: K
            value: [1.0, 2.0, 3.0]
            description: from experiment 1
          angle:
            ontology_label: null
            ontology_iri: null
            unit: rad
            value: [0.0, 0.5, 0.7]
            description: null
          demag_factor:
            ontology_label: DemagnetizingFactor
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
            unit: ''
            value: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333]
            description: ''
          comment:
            ontology_label: null
            ontology_iri: null
            unit: null
            value: [Some comment, Some other comment, A third comment]
            description: null
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    read_data = me.from_yaml(tmp_path / "data.yaml")

    assert read_data.description == "File description."
    assert read_data.Ms == me.Ms([600, 650, 700], "kA/m")
    assert me.T([1, 2, 3]) == read_data.T
    assert read_data.T.description == "from experiment 1"
    assert all(read_data.angle == [0, 0.5, 0.7] * u.rad)
    assert read_data.demag_factor == me.Entity(
        "DemagnetizingFactor", [1 / 3, 1 / 3, 1 / 3]
    )
    assert list(read_data.comment) == [
        "Some comment",
        "Some other comment",
        "A third comment",
    ]


def test_write_read_yaml_multi_shape(tmp_path):
    T = me.T([1, 2, 3])
    Tc = me.Tc(100)
    multi_index = [[1, 2], [3, 4]]

    me.EntityCollection(
        T=T,
        Tc=Tc,
        multi_index=multi_index,
    ).to_yaml(tmp_path / "example.yaml")

    read_data = me.from_yaml(tmp_path / "example.yaml")

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
        me.from_csv(tmp_path / "data.csv")


def test_no_mixed_shape_in_csv():
    with pytest.raises(ValueError):
        me.EntityCollection(
            T=me.T([1, 2, 3]),
            Tc=me.Tc(100),
        ).to_csv("will-not-be-written.csv")


def test_no_multi_dim_in_csv():
    with pytest.raises(ValueError):
        me.EntityCollection(
            T=me.T([[1, 2, 3]]),
        ).to_csv("will-not-be-written.csv")


def test_wrong_file_version_yaml(tmp_path):
    file_content = textwrap.dedent(
        """\
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
        me.from_yaml(tmp_path / "data.yaml")


def test_empty_csv(tmp_path):
    (tmp_path / "data.csv").touch()
    with pytest.raises(RuntimeError):
        me.from_csv(tmp_path / "data.csv")


def test_empty_yaml(tmp_path):
    (tmp_path / "data.yaml").touch()
    with pytest.raises(RuntimeError):
        me.from_yaml(tmp_path / "data.yaml")


def test_no_data_yaml(tmp_path):
    file_content = textwrap.dedent(
        """
        metadata:
          version: v1
          description: null
        data:
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    with pytest.raises(RuntimeError):
        me.from_yaml(tmp_path / "data.yaml")


@pytest.mark.skip(reason="Does it make sense to check IRIs when reading a file?")
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
        edge_length=[1, 2, 3] * me.units.mm,
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
