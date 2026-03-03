import os
import textwrap

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

    with pytest.raises(RuntimeError, match="Reading mammos csv v0 is not supported."):
        me.from_csv(tmp_path / "data.csv")


def test_missing_file_version_csv(tmp_path):
    file_content = textwrap.dedent(
        """\
        # not a mammos version line
        Ms
        1
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(RuntimeError, match="Cannot read version information"):
        me.from_csv(tmp_path / "data.csv")


def test_read_csv_error_for_unterminated_description_block(tmp_path):
    file_content = textwrap.dedent(
        """\
        #mammos csv v2
        #----------------------------------------
        # unterminated description block
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(RuntimeError, match="description block is not terminated"):
        me.from_csv(tmp_path / "data.csv")


def test_read_csv_error_for_truncated_v3_metadata_rows(tmp_path):
    file_content = textwrap.dedent(
        """\
        # mammos csv v3
        SpontaneousMagnetization
        first line
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(RuntimeError, match="CSV metadata is incomplete"):
        me.from_csv(tmp_path / "data.csv")


def test_read_csv_error_for_metadata_data_column_mismatch(tmp_path):
    file_content = textwrap.dedent(
        """\
        # mammos csv v3
        SpontaneousMagnetization,
        ,
        https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25,
        kA / m,
        Ms
        600.0
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(
        RuntimeError, match="CSV metadata columns and data columns do not match."
    ):
        me.from_csv(tmp_path / "data.csv")


def test_read_csv_error_for_empty_data_table(tmp_path):
    file_content = textwrap.dedent(
        """\
        # mammos csv v3
        SpontaneousMagnetization
        first line
        https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25
        kA / m
        """
    )
    (tmp_path / "data.csv").write_text(file_content)

    with pytest.raises(RuntimeError, match="CSV data table is empty."):
        me.from_csv(tmp_path / "data.csv")


def test_csv_nested_collection_not_supported(tmp_path):
    collection = me.EntityCollection(
        inner=me.EntityCollection(description="nested", value=1),
    )

    with pytest.raises(ValueError, match="Nested collections cannot be saved to CSV."):
        collection.to_csv(tmp_path / "data.csv")


def test_csv_empty_collection_not_supported(tmp_path):
    collection = me.EntityCollection(description="only metadata")

    with pytest.raises(ValueError, match="Empty collections cannot be saved to CSV."):
        collection.to_csv(tmp_path / "data.csv")


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


def test_empty_csv(tmp_path):
    (tmp_path / "data.csv").touch()
    with pytest.raises(RuntimeError, match="Cannot read version information"):
        me.from_csv(tmp_path / "data.csv")
