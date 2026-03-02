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


def test_read_yaml_v2_flat(tmp_path):
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


def test_read_yaml_v2_nested(tmp_path):
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


def test_write_yaml_key_types(tmp_path):
    sample = me.EntityCollection(
        description="Sample 1",
        Tc=me.Tc(600, "K"),
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

    assert set(file_content["data"]["Tc"]) == {
        "ontology_label",
        "description",
        "ontology_iri",
        "unit",
        "value",
    }
    assert isinstance(file_content["data"]["Tc"]["description"], str)
    assert isinstance(file_content["data"]["Tc"]["ontology_iri"], str)
    assert isinstance(file_content["data"]["Tc"]["unit"], str)
    assert set(file_content["data"]["notes"]) == {"value"}

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

    read_data = me.from_yaml(filename)
    assert read_data.description == sample.description
    assert read_data.properties.description == sample.properties.description
    assert read_data.properties.Ms == sample.properties.Ms
    assert all(read_data.properties.angle == sample.properties.angle)
    assert read_data.notes == sample.notes


def test_write_yaml_error_for_empty_collection(tmp_path):
    collection = me.EntityCollection(description="empty")

    with pytest.raises(ValueError, match="Empty collections cannot be saved to YAML."):
        collection.to_yaml(tmp_path / "data.yaml")


def test_write_read_yaml_with_empty_nested_collection(tmp_path):
    collection = me.EntityCollection(
        description="outer",
        inner=me.EntityCollection(description="empty"),
    )

    filename = tmp_path / "data.yaml"
    collection.to_yaml(filename)
    read_data = me.from_yaml(filename)
    assert isinstance(read_data.inner, me.EntityCollection)
    assert read_data.inner.description == "empty"
    assert len(read_data.inner) == 0


def test_read_yaml_error_includes_full_collection_path(tmp_path):
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

    message = str(exc_info.value)
    assert 'Entry "outer.inner" is an invalid collection in mammos yaml v2' in message


def test_read_yaml_error_includes_full_entity_path_with_dotted_key(tmp_path):
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

    message = str(exc_info.value)
    assert (
        'Entry "outer.dotted.inner.Ms" is an invalid entity-like in mammos yaml v2'
        in message
    )


def test_read_yaml_error_for_null_ontology_label(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: Top-level description.
        data:
          Ms:
            ontology_label: null
            description: ''
            ontology_iri: null
            unit: kA / m
            value: [600.0, 650.0, 700.0]
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)

    message = str(exc_info.value)
    assert (
        'Entry "Ms" is an invalid entity-like in mammos yaml v2: key '
        '"ontology_label" must be a string'
    ) in message


def test_read_yaml_error_for_invalid_top_level_description_type(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: null
        data:
          value:
            value: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)

    message = str(exc_info.value)
    assert (
        'Entry "top-level collection" is an invalid collection in mammos yaml v2'
        in message
    )
    assert 'key "description" must be a string' in message


def test_read_yaml_error_for_non_string_entity_description(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: Top-level description.
        data:
          Ms:
            ontology_label: SpontaneousMagnetization
            description: [not, a, string]
            ontology_iri: https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
            unit: kA / m
            value: [600.0, 650.0, 700.0]
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)

    message = str(exc_info.value)
    assert (
        'Entry "Ms" is an invalid entity-like in mammos yaml v2: key '
        '"description" must be a string'
    ) in message


@pytest.mark.parametrize(
    "file_content",
    [
        "description: x\ndata: {}\n",
        "metadata: []\ndescription: x\ndata: {}\n",
        "metadata: {}\ndescription: x\ndata: {}\n",
    ],
)
def test_read_yaml_error_for_missing_metadata_version(tmp_path, file_content):
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(
        RuntimeError, match="File does not have a key metadata:version."
    ):
        me.from_yaml(filename)


def test_read_yaml_error_for_invalid_v2_top_level_keys(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data: {}
        extra: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError, match="must have exactly three top-level keys"):
        me.from_yaml(filename)


def test_read_yaml_error_for_non_mapping_v2_data(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)
    assert 'key "data" must be a mapping' in str(exc_info.value)


def test_read_yaml_error_for_empty_v2_top_level_data(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data: {}
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)
    assert (
        'Entry "top-level collection" is an invalid collection in mammos yaml v2'
        in str(exc_info.value)
    )
    assert 'key "data" does not contain anything.' in str(exc_info.value)


def test_read_yaml_with_empty_v2_nested_collection_data(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data:
          inner:
            description: inner
            data: {}
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    read_data = me.from_yaml(filename)
    assert isinstance(read_data.inner, me.EntityCollection)
    assert read_data.inner.description == "inner"
    assert len(read_data.inner) == 0


def test_read_yaml_error_for_non_string_ontology_iri(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data:
          Ms:
            ontology_label: SpontaneousMagnetization
            description: ''
            ontology_iri: null
            unit: A / m
            value: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)
    assert 'key "ontology_iri" must be a string' in str(exc_info.value)


def test_read_yaml_error_for_mapping_without_collection_or_leaf_keys(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data:
          item:
            wrong: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)
    assert 'Entry "item" is an invalid entity-like in mammos yaml v2' in str(
        exc_info.value
    )


def test_read_yaml_error_prefers_entity_like_when_leaf_hints_are_present(tmp_path):
    file_content = textwrap.dedent(
        """\
        metadata:
          version: v2
        description: ok
        data:
          item:
            description: maybe a collection
            data: {}
            unit: A / m
            value: 1
        """
    )
    filename = tmp_path / "data.yaml"
    filename.write_text(file_content)

    with pytest.raises(RuntimeError) as exc_info:
        me.from_yaml(filename)
    assert 'Entry "item" is an invalid entity-like in mammos yaml v2' in str(
        exc_info.value
    )


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
