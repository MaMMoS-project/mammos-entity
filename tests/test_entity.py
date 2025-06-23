import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me

# %% initialize with float


def test_init_float():
    e = me.Entity("ExternalMagneticField", value=8e5)
    q = 8e5 * u.A / u.m
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 8e5)
    assert e.unit == u.A / u.m


# %% initialize Python types


def test_init_list():
    val = [42, 42, 42]
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    e_1 = me.Entity("ExternalMagneticField", value=val[1])
    e_2 = me.Entity("ExternalMagneticField", value=val[2])
    val[1] = 1
    val[2] = 2
    assert np.allclose(e_1.value, 42)
    assert np.allclose(e_2.value, 42)


def test_init_tuple():
    val = (42, 42, 42)
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, np.array(val))


# %% Initialize from numpy array


def test_init_numpy():
    val = np.array([42, 42, 42])
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    e_1 = me.Entity("ExternalMagneticField", value=val[1])
    e_2 = me.Entity("ExternalMagneticField", value=val[2])
    val[1] = 1
    val[2] = 2
    assert np.allclose(e_1.value, 42)
    assert np.allclose(e_2.value, 42)
    val = np.ones((42, 42, 42, 3))
    e = me.Entity("ExternalMagneticField", value=val)
    assert np.allclose(e.value, val)


# %% initialize with quantity


def test_init_quantity():
    q = 1 * u.A / u.m
    e = me.Entity("ExternalMagneticField", value=q)
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
    e = me.Entity("ExternalMagneticField", value=q, unit=" MA/m")
    assert u.allclose(e.quantity, q)
    assert np.allclose(e.value, 1e-3)
    assert e.unit == u.MA / u.m


# %% initialize with entity


def test_init_entity():
    e_1 = me.Entity("ExternalMagneticField", value=1)
    e_2 = me.Entity("ExternalMagneticField", value=e_1)
    assert u.allclose(e_1.quantity, e_2.quantity)
    assert np.allclose(e_1.value, e_2.value)
    assert e_1.unit == e_2.unit
    e_3 = me.Entity("ExternalMagneticField", value=e_1, unit="mA/m")
    assert u.allclose(e_3.quantity, e_1.quantity)
    assert np.allclose(e_3.value, 1e3)
    assert e_3.unit == u.mA / u.m


def test_check_init_unit():
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
        me.Entity("SpontaneousMagnetization", value=1 * u.T, unit="A/m")


# %% check attributes


def test_attrs_H():
    e = me.Entity("ExternalMagneticField")
    assert hasattr(e, "ontology_label")
    assert hasattr(e, "ontology_label_with_iri")
    assert hasattr(e, "ontology")
    assert hasattr(e, "quantity")
    assert hasattr(e, "value")
    assert hasattr(e, "unit")
    assert hasattr(e, "axis_label")


# %% Check repr, str


def test_repr_H():
    a = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    e = me.Entity("ExternalMagneticField", value=a)
    assert (
        e.__repr__()
        == f"Entity(ontology_label='ExternalMagneticField', value={np.array(a, dtype=float)!r}, unit='A / m')"
    )
    assert eval(repr(e)) == e


def test_repr_Tc():
    e = me.Entity("CurieTemperature")
    assert (
        e.__repr__()
        == "Entity(ontology_label='CurieTemperature', value=np.float64(0.0), unit='K')"
    )
    assert eval(repr(e)) == e


def test_repr_unitless():
    e = me.Entity("DemagnetizingFactor")
    assert (
        e.__repr__()
        == "Entity(ontology_label='DemagnetizingFactor', value=np.float64(0.0))"
    )
    assert eval(repr(e)) == e


def test_axis_label_H():
    e = me.Entity("ExternalMagneticField")
    assert e.axis_label == "External Magnetic Field (A / m)"


def test_axis_label_Ms():
    e = me.Entity("SpontaneousMagnetization")
    assert e.axis_label == "Spontaneous Magnetization (A / m)"


def test_axis_label_Tc():
    e = me.Entity("CurieTemperature")
    assert e.axis_label == "Curie Temperature (K)"


def test_axis_label_unitless():
    e = me.Entity("DemagnetizingFactor")
    assert e.axis_label == "Demagnetizing Factor"


def test_axis_label_angle():
    e = me.Entity("Angle")
    assert e.axis_label == "Angle (rad)"


# %% Check labels


@pytest.mark.parametrize("ontology_element", me.mammos_ontology.classes(imported=True))
def test_all_labels_ontology(ontology_element):
    print(ontology_element)
    me.Entity(ontology_element.prefLabel[0], 42)


def test_ontology_label_H():
    e = me.Entity("ExternalMagneticField")
    assert e.ontology_label == "ExternalMagneticField"
    assert (
        e.ontology_label_with_iri
        == "ExternalMagneticField https://w3id.org/emmo/domain/magnetic_material#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    )
    assert e.ontology_label in me.mammos_ontology
    H = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{H.prefLabel[0]} {H.iri}"


def test_ontology_label_AngularVelocity():
    e = me.Entity("AngularVelocity")
    assert e.ontology_label == "AngularVelocity"
    assert (
        e.ontology_label_with_iri
        == "AngularVelocity https://w3id.org/emmo#EMMO_bd325ef5_4127_420c_83d3_207b3e2184fd"
    )
    assert e.ontology_label in me.mammos_ontology
    omega = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{omega.prefLabel[0]} {omega.iri}"


# %% equivalencies


def test_eq():
    e_1 = me.Entity("SpontaneousMagnetization", value=1)
    e_2 = me.Entity("SpontaneousMagnetization", value=1)
    assert e_1 == e_2
    e_3 = me.Entity("SpontaneousMagnetization", value=2)
    assert e_1 != e_3
    e_4 = me.Entity("ExternalMagneticField", value=1)
    assert e_1 != e_4
    e_5 = me.Entity("SpontaneousMagnetization", value=1000, unit=u.mA / u.m)
    assert e_1 == e_5


# %% Check predefined entities


@pytest.mark.parametrize(
    "function, expected_label",
    (
        (me.A, "ExchangeStiffnessConstant"),
        (me.B, "MagneticFluxDensity"),
        # ...
    ),
)
def test_known_labels(function, expected_label):
    assert function().ontology_label == expected_label
