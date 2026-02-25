import textwrap

import mammos_units as u
import pytest
import yaml

import mammos_entity as me


def test_scalar_column_yaml(tmp_path):
    data = me.EntityCollection(A=1.0, Ms=2 * u.A / u.m, Ku=me.Ku(3))
    data.to_yaml(tmp_path / "test.yaml")

    read_data = me.from_yaml(tmp_path / "test.yaml")

    assert data["A"] == read_data.A
    assert data["Ms"] == read_data.Ms
    assert data["Ku"] == read_data.Ku


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
            unit: rad
            value: [0.0, 0.5, 0.7]
          demag_factor:
            ontology_label: DemagnetizingFactor
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_0f2b5cc9-d00a-5030-8448-99ba6b7dfd1e
            unit: ''
            value: [0.3333333333333333, 0.3333333333333333, 0.3333333333333333]
            description: ''
          comment:
            value: [Some comment, Some other comment, A third comment]
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


def test_write_yaml_v2_key_types(tmp_path):
    outer = me.EntityCollection(
        description="outer",
        Ms=me.Ms(1.2e6),
        angle=0.5 * u.rad,
        comment="text",
    )
    filename = tmp_path / "types.yaml"
    outer.to_yaml(filename)

    with open(filename) as f:
        file_content = yaml.safe_load(f)

    assert isinstance(file_content["description"], str)

    assert set(file_content["data"]["Ms"]) == {
        "ontology_label",
        "description",
        "ontology_iri",
        "unit",
        "value",
    }
    assert isinstance(file_content["data"]["Ms"]["description"], str)
    assert isinstance(file_content["data"]["Ms"]["ontology_iri"], str)
    assert isinstance(file_content["data"]["Ms"]["unit"], str)

    assert set(file_content["data"]["angle"]) == {"unit", "value"}
    assert isinstance(file_content["data"]["angle"]["unit"], str)

    assert set(file_content["data"]["comment"]) == {"value"}


def test_read_yaml_v2_nested_collection(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: Top-level description.
        data:
          sample:
            description: Sample 1
            data:
              properties:
                description: Intrinsic properties
                data:
                  Ms:
                    ontology_label: SpontaneousMagnetization
                    ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
                    unit: kA / m
                    value: [600.0, 650.0, 700.0]
                    description: ''
                  angle:
                    unit: rad
                    value: [0.0, 0.5, 0.7]
              notes:
                value: measured in setup A
          T:
            ontology_label: ThermodynamicTemperature
            ontology_iri: https://w3id.org/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f
            unit: K
            value: [300.0, 350.0, 400.0]
            description: measurement conditions
        """
    )
    (tmp_path / "data.yaml").write_text(file_content)
    read_data = me.from_yaml(tmp_path / "data.yaml")

    assert isinstance(read_data, me.EntityCollection)
    assert read_data.description == "Top-level description."
    assert isinstance(read_data.sample, me.EntityCollection)
    assert read_data.sample.description == "Sample 1"
    assert isinstance(read_data.sample.properties, me.EntityCollection)
    assert read_data.sample.properties.description == "Intrinsic properties"
    assert read_data.sample.properties.Ms == me.Ms([600, 650, 700], "kA/m")
    assert all(read_data.sample.properties.angle == [0, 0.5, 0.7] * u.rad)
    assert read_data.sample.notes == "measured in setup A"
    assert me.T([300, 350, 400], "K") == read_data.T
    assert read_data.T.description == "measurement conditions"


def test_write_yaml_v2_nested_collection_key_types(tmp_path):
    sample = me.EntityCollection(
        description="Sample 1",
        properties=me.EntityCollection(
            description="Intrinsic properties",
            Ms=me.Ms([600, 650, 700], "kA/m"),
            angle=[0, 0.5, 0.7] * u.rad,
        ),
        notes="measured in setup A",
    )

    filename = tmp_path / "nested.yaml"
    sample.to_yaml(filename)

    with open(filename) as f:
        file_content = yaml.safe_load(f)

    properties = file_content["data"]["properties"]
    assert set(properties) == {"description", "data"}
    assert isinstance(properties["description"], str)
    assert set(properties["data"]["Ms"]) == {
        "ontology_label",
        "description",
        "ontology_iri",
        "unit",
        "value",
    }
    assert set(properties["data"]["angle"]) == {"unit", "value"}
    assert set(file_content["data"]["notes"]) == {"value"}

    read_data = me.from_yaml(filename)
    assert read_data.description == sample.description
    assert read_data.properties.description == sample.properties.description
    assert read_data.properties.Ms == sample.properties.Ms
    assert all(read_data.properties.angle == sample.properties.angle)
    assert read_data.notes == sample.notes


def test_read_yaml_v2_error_includes_full_collection_path(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: Top-level description.
        data:
          outer:
            description: Outer collection
            data:
              inner:
                description: Inner collection
                invalid: {}
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)

    assert "outer.inner" in str(exc_info.value)


def test_read_yaml_v2_error_includes_full_entity_path_with_dotted_key(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: Top-level description.
        data:
          outer:
            description: Outer collection
            data:
              dotted.inner:
                description: Inner collection
                data:
                  Ms:
                    unit: A / m
                    value: [600.0, 650.0, 700.0]
                    wrong: true
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)

    assert "outer.dotted.inner.Ms" in str(exc_info.value)


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
@pytest.mark.parametrize("extension", ["yaml", "yml"])
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
