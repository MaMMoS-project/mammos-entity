import math

import astropy
import mammos_units as u
import numpy as np
import pytest
from numpy import array  # noqa: F401  # required for repr eval

import mammos_entity as me
from mammos_entity import Entity  # noqa: F401  # required for repr eval


def test_subclass():
    """Test QuantityEntity subclass of Entity."""
    e1 = me.Entity("CurieTemperature", value=0.4, unit="kK", description="Estimated via Kuz'min model.")
    e2 = me.QuantityEntity("CurieTemperature", value=400, unit="K", description="Estimated via Kuz'min model.")
    assert e1 == e2
    assert e1.description == e2.description


def test_init_float():
    """Initialize QuantityEntity instance with a float."""
    e = me.QuantityEntity("ExternalMagneticField", value=8e5)
    q = 8e5 * u.A / u.m
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 8e5)
    assert e.unit == u.A / u.m
    assert e.ontology_label == "ExternalMagneticField"


def test_init_list():
    """Initialize with Python lists."""
    val = [42, 42, 42]
    e = me.QuantityEntity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])


def test_init_tuple():
    """Initialize with Python tuples."""
    val = (42, 42, 42)
    e = me.QuantityEntity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, np.array(val))


def test_init_numpy():
    """Initialize with NumPy array."""
    val = np.array([42, 42, 42])
    e = me.QuantityEntity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    val = np.ones((42, 42, 42, 3))
    e = me.QuantityEntity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)


def test_init_quantity():
    """Initialize using mammos_units.Quantity.

    Test 1: an entity created from a quantity without specifying unit
    will take value and unit from the quantity. In this case the unit
    of the quantity is the default ontology quantity.
    Test 2: an entity created from a quantity specifying the unit
    will convert the quantity to the selected unit. In this case
    the unit is the same of the quantity, so there is actually no
    conversion involved.
    Test 3: Same as Test 1, but this time the unit of the quantity
    is not the default ontology quantity.
    Test 4: Same as Test 2, but there is an actually conversion involved.
    """
    q = 1 * u.A / u.m
    e = me.QuantityEntity("ExternalMagneticField", value=q)
    assert e.ontology_label == "ExternalMagneticField"
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.A / u.m
    q = 1 * u.kA / u.m
    e = me.QuantityEntity("ExternalMagneticField", value=q, unit="kA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.QuantityEntity("ExternalMagneticField", value=q)
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.QuantityEntity("ExternalMagneticField", value=q, unit="MA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1e-3)
    assert e.unit == u.MA / u.m


def test_init_entity():
    """Initialize from another QuantityEntity.

    Test 1: a QuantityEntity initialized from another QuantityEntity will
    define its Quantity (including unit) from it.
    Test 2: if we select a different unit, it gets converted.
    Test 3: if we initialize using an QuantityEntity with a different
    ontology label we get an error.
    """
    e_1 = me.QuantityEntity("ExternalMagneticField", value=1, unit="mA/m")
    e_2 = me.QuantityEntity("ExternalMagneticField", value=e_1)
    assert e_2.ontology_label == "ExternalMagneticField"
    assert u.allclose(e_1.quantity, e_2.quantity)
    assert np.allclose(e_1.value, e_2.value)
    assert e_1.unit == e_2.unit
    e_3 = me.QuantityEntity("ExternalMagneticField", value=e_1, unit="A/m")
    assert u.allclose(e_3.quantity, e_1.quantity)
    assert np.allclose(e_3.value, 1e-3)
    assert e_3.unit == u.A / u.m
    with pytest.raises(ValueError):
        me.QuantityEntity("CurieTemperature", value=e_1)


def test_unitless():
    """Test unitless QuantityEntity."""
    e_1 = me.QuantityEntity("DemagnetizingFactor", 0.3)
    assert e_1.ontology_label == "DemagnetizingFactor"
    assert math.isclose(e_1.value, 0.3)
    assert e_1.unit.is_equivalent("")
    e_2 = me.QuantityEntity("DemagnetizingFactor", [1, 2])
    assert np.allclose(e_2.value, [1, 2])
    assert e_2.unit.is_equivalent("")
    e_3 = me.QuantityEntity("DemagnetizingFactor", u.Quantity(0.3))
    assert math.isclose(e_3.value, 0.3)
    assert e_3.unit.is_equivalent("")
    e_4 = me.QuantityEntity("DemagnetizingFactor", e_3)
    assert math.isclose(e_4.value, 0.3)
    assert e_4.unit.is_equivalent("")


def test_check_units():
    """Test units of QuantityEntity.

    Test 1: Check that unit is immutable.
    Test 2: Check that QuantityEntity cannot be initialized with wrong unit.
    Even if we activate the necessary conversion equivalency, the initialization
    should reset all equivalencies.
    """
    # change unit (conversion/change unit after initialized entity)
    e = me.Entity("SpontaneousMagnetization", value=1, unit=u.A / u.m)
    e.quantity.to("kA/m")
    assert e.unit == u.A / u.m
    e.quantity.to("kA/m", copy=False)
    assert e.unit == u.A / u.m
    with pytest.raises(ValueError, match="incompatible with ontology. Allowed units"):
        me.QuantityEntity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(ValueError, match="incompatible with ontology. Allowed units"),
    ):
        me.QuantityEntity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(astropy.units.UnitConversionError),
    ):
        me.QuantityEntity("SpontaneousMagnetization", value=1 * u.T, unit="A/m")


def test_axis_labels():
    """Test different axis_label examples."""
    e_1 = me.QuantityEntity("ExternalMagneticField")
    assert e_1.axis_label == "External Magnetic Field (A / m)"
    e_2 = me.QuantityEntity("AffinityOfAChemicalReaction")
    assert e_2.axis_label == "Affinity Of A Chemical Reaction (J / mol)"
    e_3 = me.QuantityEntity("DemagnetizingFactor")
    assert e_3.axis_label == "Demagnetizing Factor"
    e_4 = me.QuantityEntity("Entropy")
    assert e_4.axis_label == "Entropy (J / K)"
    e_5 = me.QuantityEntity("PlanckConstant")
    assert e_5.axis_label == "Planck Constant (J s)"


def test_default_unit():
    """Test default unit for different entities."""
    assert me.QuantityEntity("MaximumEnergyProduct").unit == u.J / u.m**3
    assert me.QuantityEntity("SpontaneousMagneticPolarisation").unit == u.T


def test_label_without_concrete_units():
    """Test the ontology entries without concrete units.

    This test checks that entries with an abstract unit but no concrete units (i.e. the
    subclasses of abstract units) are initialized with units given from their dimension
    strings.

    For example, ``MagneticMoment`` has the abstract unit ``ElectricCurrentAreaUnit``.
    This abstract unit is not tied to any concrete unit, i.e. it has no subclasses.
    However, it has the attribute ``hasDimensionString`` is equal to
    ``'T0 L+2 M0 I+1 Θ0 N0 J0'`` and we read this instead.
    """
    assert me.QuantityEntity("MagneticMoment").unit == u.A * u.m**2
    assert me.QuantityEntity("DiffusionCoefficient").unit == u.m**2 / u.s
    assert me.QuantityEntity("DiffusionCoefficientForParticleNumberDensity").unit == u.m**2 / u.s
    assert me.QuantityEntity("EffectiveDiffusionCoefficient").unit == u.m**2 / u.s
    assert me.QuantityEntity("ElectricDipoleMoment").unit == u.A * u.m * u.s
    assert me.QuantityEntity("EnergyDensityOfStates").unit == u.s**2 / u.m**5 / u.kg
    assert me.QuantityEntity("JouleThomsonCoefficient").unit == u.K * u.s**2 * u.m / u.kg
    assert me.QuantityEntity("LorenzCoefficient").unit == u.m**4 * u.kg**2 / u.A**2 / u.s**6
    assert me.QuantityEntity("MagneticMomentPerUnitMass").unit == u.m**2 * u.A / u.kg
    assert me.QuantityEntity("Mobility").unit == u.A * u.s**2 / u.kg


def test_switch_to_pref_label():
    """Test the switch to prefLabel instead of given one."""
    assert me.QuantityEntity("Ms").ontology_label == "SpontaneousMagnetization"
    assert me.QuantityEntity("K1").ontology_label == "MagnetocrystallineAnisotropyConstantK1"
    assert me.QuantityEntity("A").ontology_label == "ExchangeStiffnessConstant"
    assert me.QuantityEntity("Js").ontology_label == "SpontaneousMagneticPolarization"


def test_ontology_information_mammos():
    """Test ontology label and IRI for an Entity in the MaMMoS ontology."""
    e = me.QuantityEntity("ExternalMagneticField")
    assert e.ontology_label == "ExternalMagneticField"
    assert e.ontology_iri == "https://w3id.org/emmo/domain/magnetic-materials#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    assert (
        e.ontology_label_with_iri
        == "ExternalMagneticField https://w3id.org/emmo/domain/magnetic-materials#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    H = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{H.prefLabel[0]} {H.iri}"


def test_ontology_information_EMMO():
    """Test ontology label and IRI for an Entity in the EMMO."""
    e = me.QuantityEntity("AngularVelocity")
    assert e.ontology_label == "AngularVelocity"
    assert e.ontology_iri == "https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    assert (
        e.ontology_label_with_iri == "AngularVelocity https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    omega = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{omega.prefLabel[0]} {omega.iri}"


def test_equality():
    """Test equality.

    We expect two quantity entities to be equal if the ontology_label is the
    same and the values are close enough.
    Equality fails when the right hand term is not an QuantityEntity.
    """
    e_1 = me.QuantityEntity("SpontaneousMagnetization", value=1)
    e_2 = me.QuantityEntity("SpontaneousMagnetization", value=1)
    assert e_1 == e_2
    e_3 = me.QuantityEntity("SpontaneousMagnetization", value=2)
    assert e_1 != e_3
    e_4 = me.QuantityEntity("ExternalMagneticField", value=1)
    assert e_1 != e_4
    e_5 = me.QuantityEntity("SpontaneousMagnetization", value=1000, unit=u.mA / u.m)
    assert e_1 == e_5
    e_6 = me.QuantityEntity("SpontaneousMagnetization", value=[[1, 1]])
    assert e_1 != e_6
    e_7 = me.QuantityEntity("SpontaneousMagnetization", value=[[1], [1]])
    assert e_6 != e_7

    # Other objects
    assert e_1 != 1 * u.A / u.m
    assert e_1 != 1
    assert e_1 != e_2.quantity
    e_8 = me.StringEntity("ChemicalComposition", "H2O")
    assert e_8 != e_1

    # Other objects can implement __eq__ in a way that is compatible with Entity

    class A:
        def __eq__(self, o):
            return True

    assert e_1 == A()


def test_bad_description():
    """Check bad type for description."""
    with pytest.raises(ValueError):
        me.QuantityEntity("SpontaneousMagnetization", description=1)


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
