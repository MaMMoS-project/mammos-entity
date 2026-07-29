import mammos_units as u
import numpy as np
import pytest
from numpy import array  # noqa: F401  # required for repr eval
from numpy.dtypes import StringDType  # noqa: F401  # required for repr eval

import mammos_entity as me
from mammos_entity import QuantityEntity, StringEntity  # noqa: F401  # required for repr eval


def test_repr():
    """Test representation string of an Entity.

    Test 1: Test repr for QuantityEntity with scalar value.
    Test 2: Test repr for QuantityEntity with scalar value and description
    Test 3: Test repr for QuantityEntity with vectorial value.
    Test 4: Test repr for unitless QuantityEntity.
    Test 5: Test repr for StringEntity
    Test 6: Test repr for StringEntity with description

    Note that the representation of floats will be slightly different for NumPy 1
    and for NumPy 2. In particular `zero_string` = `'0.0'` for NumPy 1,
    and = `'np.float64(0.0)'` for NumPy 2.
    """
    e = me.Entity("CurieTemperature")
    zero_string = f"{np.float64(0.0)!r}"  # differs for NumPy 1 and NumPy 2.
    assert e.__repr__() == f"QuantityEntity(ontology_label='CurieTemperature', value={zero_string}, unit='K')"
    assert eval(repr(e)) == e

    e = me.Entity("CurieTemperature", description="Estimated.")
    assert (
        e.__repr__()
        == f"QuantityEntity(ontology_label='CurieTemperature', value={zero_string}, unit='K', description='Estimated.')"
    )
    assert eval(repr(e)) == e

    a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    e = me.Entity("ExternalMagneticField", value=a)
    assert e.__repr__() == (
        "QuantityEntity(ontology_label='ExternalMagneticField', " + f"value={np.array(a, dtype=float)!r}, unit='A / m')"
    )
    assert eval(repr(e)) == e

    e = me.Entity("DemagnetizingFactor")
    assert e.__repr__() == f"QuantityEntity(ontology_label='DemagnetizingFactor', value={zero_string})"
    assert eval(repr(e)) == e

    value = "Nd2Fe14B"
    value_repr = f"{np.array(value, dtype=np.dtypes.StringDType)!r}"
    e = me.StringEntity("ChemicalComposition", value=value)
    assert e.__repr__() == f"StringEntity(ontology_label='ChemicalComposition', value={value_repr})"
    assert eval(repr(e)) == e

    e = me.StringEntity("ChemicalComposition", value=value, description="experiment 2")
    assert (
        e.__repr__()
        == f"StringEntity(ontology_label='ChemicalComposition', value={value_repr}, description='experiment 2')"
    )
    assert eval(repr(e)) == e


def test_str():
    """Test readable string of an Entity.

    Test 1: Test repr for QuantityEntity with scalar value.
    Test 2: Test repr for QuantityEntity with scalar value and description
    Test 3: Test repr for QuantityEntity with 1D-vectorial value.
    Test 4: Test repr for QuantityEntity with 2D-vectorial value.
    Test 5: Test repr for unitless QuantityEntity.
    Test 6: Test repr for StringEntity with no value
    Test 7: Test repr for StringEntity with value only
    Test 8: Test repr for StringEntity with description only
    Test 9: Test repr for StringEntity with value and description
    """
    e = me.Entity("CurieTemperature")
    assert str(e) == "CurieTemperature(0.0 K)"

    e = me.Entity("CurieTemperature", description="Estimated.")
    assert str(e) == "CurieTemperature(0.0 K, description='Estimated.')"

    e = me.Entity("ExternalMagneticField", value=[1, 2, 3])
    assert str(e) == "ExternalMagneticField([1. 2. 3.] A / m)"

    a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    e = me.Entity("ExternalMagneticField", value=a)
    assert str(e) == f"ExternalMagneticField({e.q!s})"

    e = me.Entity("DemagnetizingFactor")
    assert str(e) == "DemagnetizingFactor(0.0)"

    e = me.StringEntity("ChemicalComposition")
    assert str(e) == "ChemicalComposition()"

    e = me.StringEntity("ChemicalComposition", value="Nd2Fe14B")
    assert str(e) == "ChemicalComposition(Nd2Fe14B)"

    e = me.StringEntity("ChemicalComposition", description="experiment 2")
    assert str(e) == "ChemicalComposition(description='experiment 2')"

    e = me.StringEntity("ChemicalComposition", value="Nd2Fe14B", description="experiment 2")
    assert str(e) == "ChemicalComposition(Nd2Fe14B, description='experiment 2')"


@pytest.mark.parametrize("ontology_element", me.mammos_ontology.classes(imported=True))
def test_all_labels_ontology(ontology_element):
    """Test creation of Entity with all labels in the ontology.

    We initialize entities without a value. This is intended as the empty
    string for StringEntity objects and as zero for QuantityEntity objects.

    Entities `Person` and `Organization` do not have a `prefLabel`.
    These are extreme, unfixable cases and we ignore them.
    """
    if ontology_element.prefLabel:
        prefLabel = str(ontology_element.prefLabel[0])
        if prefLabel in [
            "Electron",
            "ElementaryCharge",
            "Grain",
            "Point",
            "RelativePermeability",
            "RelativePermittivity",
        ]:
            pytest.xfail(f"{prefLabel=} is ambiguous")
        me.Entity(prefLabel)


@pytest.mark.parametrize(
    "function, expected_label",
    (
        (me.A, "ExchangeStiffnessConstant"),
        (me.BHmax, "MaximumEnergyProduct"),
        (me.B, "MagneticFluxDensity"),
        (me.H, "ExternalMagneticField"),
        (me.Hc, "CoercivityHcExternal"),
        (me.J, "MagneticPolarisation"),
        (me.Js, "SpontaneousMagneticPolarization"),
        (me.K1, "MagnetocrystallineAnisotropyConstantK1"),
        (me.K2, "MagnetocrystallineAnisotropyConstantK2"),
        (me.Ku, "UniaxialAnisotropyConstant"),
        (me.M, "Magnetization"),
        (me.Mr, "Remanence"),
        (me.Ms, "SpontaneousMagnetization"),
        (me.T, "ThermodynamicTemperature"),
        (me.Tc, "CurieTemperature"),
    ),
)
def test_known_labels(function, expected_label):
    """Check predefined entities."""
    assert function().ontology_label == expected_label


def test_bad_description():
    """Check bad type for description."""
    with pytest.raises(ValueError):
        me.Ms(1, description=1)


@pytest.mark.parametrize(
    "value, expected_value, expected_unit",
    [
        (me.Entity("ThermodynamicTemperature", 300.0 * u.K), 300.0, u.K),
        (300.0 * u.K, 300.0, u.K),
        (300.0, 300.0, u.deg_C),
        (
            me.Entity("ThermodynamicTemperature", [100.0, 200.0, 300.0] * u.K),
            [100.0, 200.0, 300.0],
            u.K,
        ),
        ([100.0, 200.0, 300.0] * u.K, [100.0, 200.0, 300.0], u.K),
        ([100.0, 200.0, 300.0], [100.0, 200.0, 300.0], u.deg_C),
    ],
)
def test_from_compatible(value, expected_value, expected_unit):
    """Test from_compatible with valid inputs."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "deg_C",
        temperature=value,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, expected_value)
    assert out.unit == expected_unit


@pytest.mark.parametrize(
    "value",
    [
        me.Entity("CurieTemperature", 300.0 * u.K),
        me.Entity("NeelTemperature", 300.0 * u.K),
        me.Entity("ThermodynamicTemperature", 300.0 * u.K),
        300.0 * u.K,
        300.0,
    ],
)
def test_from_compatible_compatible_entity(value):
    """Test from_compatible with a compatible entity."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "K",
        compatible_entities=("CurieTemperature", "NeelTemperature"),
        temperature=value,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, 300.0)
    assert out.unit == u.K


def test_from_compatible_enforce_unit():
    """Test from_compatible with enforce_unit=True."""
    out = me._entity.from_compatible(
        "ThermodynamicTemperature",
        "deg_C",
        enforce_unit=True,
        temperature=300 * u.K,
    )
    assert out.ontology_label == "ThermodynamicTemperature"
    assert np.allclose(out.value, 26.85)
    assert out.unit == u.deg_C


@pytest.mark.parametrize(
    "value, expected_error",
    [
        (me.Entity("ExternalMagneticField", 1), ValueError),
        (1 * u.m, ValueError),
        ("String", TypeError),
        ([1, 2, "String"], TypeError),
        (
            [
                me.Entity("ThermodynamicTemperature", [100.0] * u.K),
                me.Entity("ThermodynamicTemperature", [200.0] * u.K),
                me.Entity("ThermodynamicTemperature", [300.0] * u.K),
            ],
            TypeError,
        ),
    ],
)
def test_from_compatible_errors(value, expected_error):
    """Test from_compatible raises on incompatible inputs."""
    with pytest.raises(expected_error):
        me._entity.from_compatible(
            "ThermodynamicTemperature",
            "deg_C",
            temperature=value,
        )


def test_from_compatible_wrong_kwarg():
    """Test from_compatible raises with wrong number of kwargs."""
    with pytest.raises(RuntimeError):
        me._entity.from_compatible("ThermodynamicTemperature", "deg_C")

    with pytest.raises(RuntimeError):
        me._entity.from_compatible(
            "ThermodynamicTemperature",
            "deg_C",
            temperature=5,
            tc=5,
        )


def test_getitem_int():
    """Entity integer indexing returns scalar entity with label/unit preserved."""
    ms = me.Ms([500, 600, 700], "kA/m", description="measured at 0 K")
    result = ms[0]
    assert result.ontology_label == "SpontaneousMagnetization"
    assert result.unit == u.kA / u.m
    assert result.description == "measured at 0 K"
    assert result.value == 500.0


def test_getitem_slice():
    """Entity slice indexing returns entity with subset of values."""
    ms = me.Ms([500, 600, 700], "kA/m")
    result = ms[1:3]
    assert np.array_equal(result.value, [600, 700])


def test_getitem_step():
    """Entity slice with step returns every Nth value."""
    ms = me.Ms([500, 600, 700, 800], "kA/m")
    result = ms[::2]
    assert np.array_equal(result.value, [500, 700])


def test_getitem_negative():
    """Negative integer indexing returns last element."""
    ms = me.Ms([500, 600, 700], "kA/m")
    result = ms[-1]
    assert result.value == 700.0


def test_getitem_bool_array():
    """Boolean array indexing selects values where mask is True."""
    ms = me.Ms([500, 600, 700, 800], "kA/m")
    result = ms[[True, False, True, False]]
    assert np.array_equal(result.value, [500, 700])


def test_getitem_int_array():
    """Integer array indexing selects values at given positions."""
    ms = me.Ms([500, 600, 700, 800], "kA/m")
    result = ms[[0, 2, 3]]
    assert np.array_equal(result.value, [500, 700, 800])


def test_getitem_multidim():
    """Multi-dimensional slicing works for 2D entity values."""
    val = [[1, 2, 3], [4, 5, 6]]
    ms = me.Ms(val, "A/m")
    row = ms[0]
    assert np.array_equal(row.value, [1, 2, 3])
    col = ms[:, 0]
    assert np.array_equal(col.value, [1, 4])


def test_getitem_preserves_ontology_label():
    """Slicing preserves ontology label."""
    ms = me.Ms([500, 600, 700], "kA/m")
    assert ms[0].ontology_label == "SpontaneousMagnetization"
    assert ms[1:3].ontology_label == "SpontaneousMagnetization"
    assert ms[[True, False, True]].ontology_label == "SpontaneousMagnetization"
    assert ms[[0, 2]].ontology_label == "SpontaneousMagnetization"


def test_getitem_preserves_unit():
    """Slicing preserves unit."""
    ms = me.Ms([500, 600, 700], "kA/m")
    assert ms[0].unit == u.kA / u.m
    assert ms[1:3].unit == u.kA / u.m


def test_getitem_preserves_description():
    """Slicing preserves description."""
    ms = me.Ms([500, 600, 700], "kA/m", description="measured at 0 K")
    assert ms[0].description == "measured at 0 K"
    assert ms[1:3].description == "measured at 0 K"


def test_getitem_scalar_entity_raises():
    """Indexing a scalar entity raises TypeError."""
    ms = me.Ms(500, "kA/m")
    with pytest.raises(TypeError, match="scalar value does not support indexing"):
        ms[0]


def test_getitem_out_of_range():
    """Index out of range raises IndexError."""
    ms = me.Ms([500, 600, 700], "kA/m")
    with pytest.raises(IndexError):
        ms[999]
