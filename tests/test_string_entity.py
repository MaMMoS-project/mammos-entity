import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me


def test_subclass():
    """Test StringEntity subclass of Entity."""
    e1 = me.Entity("ChemicalComposition", "Nd2Fe14B", description="Formula without doping.")
    e2 = me.StringEntity("ChemicalComposition", "Nd2Fe14B", description="Formula without doping.")
    assert e1 == e2


def test_fields():
    """Test fields of a StringEntity."""
    e = me.StringEntity("ChemicalComposition", "Nd2Fe14B", description="Formula without doping.")
    assert e.ontology_label == "ChemicalComposition"
    assert e.value == "Nd2Fe14B"
    assert e.description == "Formula without doping."
    assert e.ontology_iri == "https://w3id.org/emmo#EMMO_7efd64d1_05a1_49cd_a7f0_783ca050d4f3"
    assert (
        e.ontology_label_with_iri
        == "ChemicalComposition https://w3id.org/emmo#EMMO_7efd64d1_05a1_49cd_a7f0_783ca050d4f3"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    assert not hasattr(e, "unit")


def test_description():
    """Test description of a StringEntity object."""
    e = me.StringEntity("ChemicalComposition")
    e.description = "updated description"
    assert e.description == "updated description"
    with pytest.raises(ValueError):
        e.description = 1


def test_init_no_value():
    """Initialize StringEntity instance without a value."""
    e = me.StringEntity("ChemicalComposition")
    assert e.value == ""
    e = me.StringEntity("ChemicalComposition", value=None)
    assert e.value == ""


def test_init_entity():
    """Initialize StringEntity instance using another StringEntity."""
    e1 = me.StringEntity("ChemicalComposition", value="Nd2Fe14B", description="old entity")
    e2 = me.StringEntity("ChemicalComposition", value=e1, description="new entity")
    assert e2.value == "Nd2Fe14B"
    assert e2.description == "new entity"
    with pytest.raises(ValueError):
        me.StringEntity("ChemicalComposition", value=me.Hc())


def test_init_different_types():
    """Test that StringEntity cannot be initialized with wrong types.

    Test 1: list of strings.
    Test 2: single integer.
    Test 3: single float.
    Test 4: list of integers.
    Test 5: tuple of integers.
    """
    assert np.all(me.StringEntity("ChemicalComposition", value=["H2", "O"]).value == np.array(["H2", "O"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=42).value == np.array(["42"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=0.5).value == np.array(["0.5"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=[1, 2, 3]).value == np.array(["1", "2", "3"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=(1, 2, 3)).value == np.array(["1", "2", "3"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=np.array([1, 2, 3])).value == np.array(["1", "2", "3"]))
    assert np.all(me.StringEntity("ChemicalComposition", value=1 * u.A / u.m).value == np.array(["1.0"]))


def test_init_unit():
    """Test behavior of StringEntity and units."""
    with pytest.xfail():
        with pytest.raises(TypeError):
            me.Entity("ChemicalComposition", value="Nd2Fe14B", unit="m")
        with pytest.raises(TypeError):
            me.StringEntity("ChemicalComposition", value="Nd2Fe14B", unit="m")


def test_equality():
    """Test equality of StringEntity.

    We expect two string entities to be equal if the ontology_label is the same
    and the string values are exactly the same.
    Equality fails when the right hand term is not an StringEntity.
    """
    e_1 = me.StringEntity("ChemicalComposition", value="H2O")
    e_2 = me.StringEntity("ChemicalComposition", value="H2O")
    assert e_1 == e_2
    e_3 = me.StringEntity("ChemicalComposition", value="H2O", description="completely different entity")
    assert e_1 == e_3
    e_4 = me.StringEntity("ChemicalComposition", value="H2O2")
    assert e_1 != e_4
    e_5 = me.StringEntity("ChemicalComposition")
    assert e_1 != e_5

    e_6 = me.StringEntity("StateOfMatter", "H2O")
    assert e_1 != e_6

    # Other objects
    assert e_1 != "H2O"
    assert e_1 != e_2.value
    e_7 = me.QuantityEntity("CurieTemperature", value=400)
    assert e_7 != e_1

    # Other objects can implement __eq__ in a way that is compatible with StringEntity

    class A:
        def __eq__(self, o):
            return True

    assert e_1 == A()


def test_bad_description():
    """Check bad type for description."""
    with pytest.raises(ValueError):
        me.StringEntity("ChemicalComposition", description=1)


def test_from_compatible():
    """Test from_compatible with valid inputs."""
    out = me._entity.from_compatible(
        "ChemicalComposition",
        chemical_composition="Nd2Fe14B",
    )
    expected = me.StringEntity("ChemicalComposition", value="Nd2Fe14B")
    assert out == expected


@pytest.mark.parametrize(
    "value",
    [
        me.StringEntity("ChemicalElement", "H"),
        me.StringEntity("ChemicalCompound", "H"),
        me.StringEntity("ChemicalComposition", "H"),
        "H",
    ],
)
def test_from_compatible_compatible_entity(value):
    """Test from_compatible with a compatible entity."""
    out = me._entity.from_compatible(
        "ChemicalComposition",
        compatible_entities=("ChemicalElement", "ChemicalCompound"),
        chemical_composition=value,
    )
    expected = me.StringEntity("ChemicalComposition", value="H")
    assert out == expected


def test_from_compatible_input_error():
    """Test from_compatible raises on incompatible inputs."""
    with pytest.raises(ValueError):
        me._entity.from_compatible(
            "ChemicalComposition",
            comp=me.StringEntity("StateOfMatter", "Solid"),
        )


def test_from_compatible_unit():
    """Test behavior of from_compatible with unit arguments usage."""
    with pytest.raises(ValueError):
        me._entity.from_compatible(
            "ChemicalComposition",
            fallback_unit="m",
            chemical_composition="H2O",
        )
    with pytest.raises(RuntimeError):
        me._entity.from_compatible(
            "ChemicalComposition",
            enforce_unit=True,
            chemical_composition="H2O",
        )
