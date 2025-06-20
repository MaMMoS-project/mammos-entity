import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me

# %% initialize with float


def test_init_float():
    e = me.H(8e5)
    q = 8e5 * u.A / u.m
    assert np.allclose(e.quantity, q)
    assert np.allclose(e.value, 8e5)
    assert e.unit == u.A / u.m


# %% initialize Python types


def test_init_list():
    val = [42, 42, 42]
    e = me.Ku(val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    e_1 = me.Ku(val[1])
    e_2 = me.Ku(val[2])
    val[1] = 1
    val[2] = 2
    assert np.allclose(e_1.value, 42)
    assert np.allclose(e_2.value, 42)


def test_init_tuple():
    val = (42, 42, 42)
    e = me.Ms(val)
    assert np.allclose(e.value, np.array(val))


# %% Initialize from numpy array


def test_init_numpy():
    val = np.array([42, 42, 42])
    e = me.H(val)
    assert np.allclose(e.value, val)
    val[0] = 1
    assert np.allclose(e.value, [42, 42, 42])
    e_1 = me.Ku(val[1])
    e_2 = me.Ku(val[2])
    val[1] = 1
    val[2] = 2
    assert np.allclose(e_1.value, 42)
    assert np.allclose(e_2.value, 42)
    val = np.ones((42, 42, 42, 3))
    e = me.H(val)
    assert np.allclose(e.value, val)


# %% initialize with quantity


def test_init_quantity():
    q = 1 * u.A / u.m
    e = me.H(q)
    assert np.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.A / u.m
    q = 1 * u.kA / u.m
    e = me.H(q, "kA/m")
    assert np.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.H(q)
    assert np.allclose(e.quantity, q)
    assert np.allclose(e.value, 1)
    assert e.unit == u.kA / u.m
    e = me.H(q, "MA/m")
    assert np.allclose(e.quantity, q)
    assert np.allclose(e.value, 1e-3)
    assert e.unit == u.MA / u.m


# %% initialize with entity


def test_init_entity():
    # same thing as quantity
    pass


def test_check_init_unit():
    # change unit (conversion/change unit after initialized entity)
    e = me.Ms(1, unit=u.A / u.m)
    e.quantity.to("kA/m")
    assert e.unit == u.A / u.m
    e.quantity.to("kA/m", copy=False)
    assert e.unit == u.A / u.m
    with pytest.raises(u.UnitConversionError):
        me.Ms(1, unit="T")
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        me.Ms(1 * u.T, "A/m")


# %% check attributes


def test_attrs_H():
    e = me.H()
    assert hasattr(e, "ontology_label")
    assert hasattr(e, "ontology_label_with_iri")
    assert hasattr(e, "ontology")
    assert hasattr(e, "quantity")
    assert hasattr(e, "value")
    assert hasattr(e, "unit")
    assert hasattr(e, "axis_label")


# %% Check repr, str


def test_repr_H():
    e = me.H([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert e.__repr__() == "Entity('ExternalMagneticField', np.float64(0.0), 'A / m')"
    assert eval(repr(e)) == e


def test_repr_Tc():
    e = me.Tc()
    assert e.__repr__() == "Entity('CurieTemperature', np.float64(0.0), 'K')"
    assert eval(repr(e)) == e


def test_repr_unitless():
    e = me.Entity("DemagnetizingFactor")
    assert e.__repr__() == "Entity('DemagnetizingFactor', np.float64(0.0))"
    assert eval(repr(e)) == e


def test_axis_label_H():
    e = me.H()
    assert e.axis_label == "External Magnetic Field (A / m)"


def test_axis_label_Ms():
    e = me.Ms()
    assert e.axis_label == "Spontaneous Magnetization (A / m)"


def test_axis_label_Tc():
    e = me.Tc()
    assert e.axis_label == "Curie Temperature (K)"


def test_axis_label_unitless():
    e = me.Entity("DemagnetizingFactor")
    assert e.axis_label == "DemagnetizingFactor"


def test_axis_label_angle():
    e = me.Entity("Angle")
    assert e.axis_label == "Angle (rad)"


# %% Check labels


@pytest.mark.parametrize("ontology_element", me.mammos_ontology.classes(imported=True))
def test_all_labels_ontology(ontology_element):
    print(ontology_element)
    me.Entity(ontology_element.prefLabel[0], 42)


def test_ontology_label_H():
    e = me.H()
    assert e.ontology_label == "ExternalMagneticField"
    assert e.ontology_label == me.mammos_ontology
    assert (
        e.ontology_label_with_iri
        == "ExternalMagneticField https://w3id.org/emmo/domain/magnetic_material#EMMO_da08f0d3-fe19-58bc-8fb6-ecc8992d5eb3"
    )
    assert e.ontology_label in me.mammos_ontology
    H = me.mammos_ontology.get_by_label(e.ontology_label)
    assert e.ontology_label_with_iri == f"{H.prefLabel[0]} {H.iri}"


def test_ontology_label_AngularVelocity():
    e = me.Entity("AngularVelocity")
    assert False


# %% equivalencies


def test_eq():
    e_1 = Ms(1)
    e_2 = Ms(1)
    assert e_1 == e_2
    e_3 = Ms(2)
    assert e_1 != e_3
    e_4 = H(1)
    assert e_1 != e_4
    e_5 = Ms(1000, u.mA / u.m)
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
