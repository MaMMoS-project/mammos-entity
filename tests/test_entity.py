import mammos_units as u
import numpy as np
import pytest
from numpy import array  # noqa: F401  # required for repr eval

import mammos_entity as me
from mammos_entity import Entity  # noqa: F401  # required for repr eval


def test_init_float():
    """Initialize Entity instance with a float."""
    e = me.Entity("ExternalMagneticField", value=8e5)
    q = 8e5 * u.A / u.m
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 8e5)
    assert e.unit == u.A / u.m
    assert e.ontology_label == "ExternalMagneticField"


def test_init_list():
    """Initialize with Python lists."""
    val = [42, 42, 42]
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])


def test_init_tuple():
    """Initialize with Python tuples."""
    val = (42, 42, 42)
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, np.array(val))


def test_init_numpy():
    """Initialize with NumPy array."""
    val = np.array([42, 42, 42])
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    val = np.ones((42, 42, 42, 3))
    e = me.Entity("ExternalMagneticField", value=val)
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
    e = me.Entity("ExternalMagneticField", value=q)
    assert e.ontology_label == "ExternalMagneticField"
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.A / u.m
    q = 1 * u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q, unit="kA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q)
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.Entity("ExternalMagneticField", value=q, unit="MA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1e-3)
    assert e.unit == u.MA / u.m


def test_init_entity():
    """Initialize from another Entity.

    Test 1: an Entity initialized from another Entity will define
    its Quantity (including unit) from it.
    Test 2: if we select a different unit, it gets converted.
    Test 3: if we initialize using an Entity with a different ontology label
    we get an error.
    """
    e_1 = me.Entity("ExternalMagneticField", value=1, unit="mA/m")
    e_2 = me.Entity("ExternalMagneticField", value=e_1)
    assert e_2.ontology_label == "ExternalMagneticField"
    assert u.allclose(e_1.quantity, e_2.quantity)
    assert np.allclose(e_1.value, e_2.value)
    assert e_1.unit == e_2.unit
    e_3 = me.Entity("ExternalMagneticField", value=e_1, unit="A/m")
    assert u.allclose(e_3.quantity, e_1.quantity)
    assert np.allclose(e_3.value, 1e-3)
    assert e_3.unit == u.A / u.m
    with pytest.raises(ValueError):
        me.Entity("CurieTemperature", value=e_1)


def test_check_units():
    """Test units of Entity.

    Test 1: Check that unit is immutable.
    Test 2: Check that Entity cannot be initialized with wrong unit.
    Even if we activate the necessary conversion equivalency, the initialization
    should reset all equivalencies.
    """
    # change unit (conversion/change unit after initialized entity)
    e = me.Entity("SpontaneousMagnetization", value=1, unit=u.A / u.m)
    e.quantity.to("kA/m")
    assert e.unit == u.A / u.m
    e.quantity.to("kA/m", copy=False)
    assert e.unit == u.A / u.m
    with pytest.raises(u.UnitConversionError):
        me.Entity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        me.Entity("SpontaneousMagnetization", value=1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        me.Entity("SpontaneousMagnetization", value=1 * u.T, unit="A/m")


def test_repr():
    """Test representation string.

    Test 1: Test repr for scalar value.
    Test 2: Test repr for vectorial value.
    Test 3: Test repr for unitless Entity.
    """
    e = me.Entity("CurieTemperature")
    assert (
        e.__repr__()
        == "Entity(ontology_label='CurieTemperature', value=np.float64(0.0), unit='K')"
    )
    assert eval(repr(e)) == e

    a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    e = me.Entity("ExternalMagneticField", value=a)
    assert e.__repr__() == (
        "Entity(ontology_label='ExternalMagneticField', "
        + f"value={np.array(a, dtype=float)!r}, unit='A / m')"
    )
    assert eval(repr(e)) == e

    e = me.Entity("DemagnetizingFactor")
    assert (
        e.__repr__()
        == "Entity(ontology_label='DemagnetizingFactor', value=np.float64(0.0))"
    )
    assert eval(repr(e)) == e


def test_axis_labels():
    """Test different axis_label examples."""
    e_1 = me.Entity("ExternalMagneticField")
    assert e_1.axis_label == "External Magnetic Field (A / m)"
    e_2 = me.Entity("AffinityOfAChemicalReaction")
    assert e_2.axis_label == "Affinity Of A Chemical Reaction (J / mol)"
    e_3 = me.Entity("DemagnetizingFactor")
    assert e_3.axis_label == "Demagnetizing Factor"
    e_4 = me.Entity("Entropy")
    assert e_4.axis_label == "Entropy (J / K)"
    # e_5 = me.Entity("PlanckConstant")
    # assert e_5.axis_label == "Planck Constant (m2 kg / s)"


@pytest.mark.parametrize("ontology_element", me.mammos_ontology.classes(imported=True))
def test_all_labels_ontology(ontology_element):
    """Test all labels in the ontology.

    This test creates one Entity instance for each label in the ontology.
    """
    me.Entity(ontology_element.prefLabel[0], 42)


def test_ontology_label_mammos():
    """Test ontology label for an Entity in the MaMMoS ontology."""
    e = me.Entity("ExternalMagneticField")
    assert e.ontology_label == "ExternalMagneticField"
    assert (
        e.ontology_label_with_iri
        == "ExternalMagneticField https://w3id.org/emmo/domain/magnetic_material#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    H = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{H.prefLabel[0]} {H.iri}"


def test_ontology_label_EMMO():
    """Test ontology label for an Entity in the EMMO."""
    e = me.Entity("AngularVelocity")
    assert e.ontology_label == "AngularVelocity"
    assert (
        e.ontology_label_with_iri
        == "AngularVelocity https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    )
    assert e.ontology_label_with_iri == f"{e.ontology.prefLabel[0]} {e.ontology.iri}"
    assert e.ontology_label in me.mammos_ontology
    omega = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{omega.prefLabel[0]} {omega.iri}"


def test_equality():
    """Test equality.

    We expect two entities to be equal if the ontology_label is the same
    and the values are close enough.
    Equality fails when the right hand term is not an Entity.
    """
    e_1 = me.Entity("SpontaneousMagnetization", value=1)
    e_2 = me.Entity("SpontaneousMagnetization", value=1)
    assert e_1 == e_2
    e_3 = me.Entity("SpontaneousMagnetization", value=2)
    assert e_1 != e_3
    e_4 = me.Entity("ExternalMagneticField", value=1)
    assert e_1 != e_4
    e_5 = me.Entity("SpontaneousMagnetization", value=1000, unit=u.mA / u.m)
    assert e_1 == e_5
    e_6 = me.Entity("SpontaneousMagnetization", value=[[1, 1]])
    assert e_1 != e_6
    e_7 = me.Entity("SpontaneousMagnetization", value=[[1], [1]])
    assert e_6 != e_7

    # Other objects
    assert e_1 != 1 * u.A / u.m
    assert e_1 != 1
    assert e_1 != e_2.quantity

    # Other objects can implement __eq__ in a way that is compatible with Entity

    class A:
        def __eq__(self, o):
            return True

    assert e_1 == A()


@pytest.mark.parametrize(
    "function, expected_label",
    (
        (me.A, "ExchangeStiffnessConstant"),
        (me.BHmax, "MaximumEnergyProduct"),
        (me.B, "MagneticFluxDensity"),
        (me.H, "ExternalMagneticField"),
        (me.Hc, "CoercivityHcExternal"),
        (me.J, "MagneticPolarisation"),
        (me.Js, "SpontaneousMagneticPolarisation"),
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
