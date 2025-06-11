import mammos_units as u
import numpy as np
import pytest

import mammos_entity as me


def test_unit_conversion():
    e = me.A(42)  # NOTE: we know that unit by default J/m
    e_same = me.A(42e3, unit="mJ/m")
    assert np.allclose(e, e_same)


def test_SI_conversion():
    e = me.BHmax(42, unit="kJ/m3")
    e_si = e.si
    assert e.ontology_label == e_si.ontology_label
    assert np.allclose(e, e_si)
    assert e_si.unit == "J/m3"


def test_to_method():
    e = me.H(8e5)
    e_same = e.to("mA/m")
    np.allclose(e, e_same)
    assert e.ontology_label == e_same.ontology_label
    e_eq = e.to("T", equivalencies=u.magnetic_flux_field())
    assert not hasattr(e_eq, "ontology_label")
    assert not isinstance(e_eq, me.Entity)
    assert isinstance(e_eq, u.Quantity)


def test_numpy_array_as_value():
    val = np.array([42, 42, 42])
    e = me.H(val)
    assert np.allclose(e.value, val)


def test_multidim_numpy_array_as_value():
    val = np.ones((42, 42, 42, 3))
    e = me.H(val)
    assert np.allclose(e.value, val)


def test_list_as_value():
    val = [42, 42, 42]
    e = me.Ku(val)
    assert np.allclose(e.value, np.array(val))


def test_tuple_as_value():
    val = (42, 42, 42)
    e = me.Ms(val)
    assert np.allclose(e.value, np.array(val))


def test_entity_drop_ontology_numpy(onto_class_list):
    for label in onto_class_list:
        e = me.Entity(label, 42)
        root_e = np.sqrt(e)
        with pytest.raises(AttributeError):
            _ = root_e.ontology


def test_entity_drop_ontology_multiply(onto_class_list):
    for label in onto_class_list:
        e = me.Entity(label, 42)
        mul_e = e * e
        with pytest.raises(AttributeError):
            _ = mul_e.ontology


def test_all_labels_ontology(onto_class_list):
    for label in onto_class_list:
        _ = me.Entity(label, 42)


def test_quantity_as_value():
    val = 1 * u.A / u.m
    e = me.Ms(val)
    assert u.allclose(e.quantity, val)


def test_wrong_quantity_as_value():
    val = 1 * u.T
    with pytest.raises(u.UnitConversionError):
        me.Ms(val)


def test_quantity_as_value_and_unit():
    val = 1 * u.A / u.m
    e = me.Ms(val, "A/m")
    assert u.allclose(e.quantity, val)


def test_wrong_quantity_as_value_and_unit():
    val = 1 * u.T
    with pytest.raises(u.UnitConversionError):
        me.Ms(val, "A/m")


def test_wrong_quantity_as_value_and_wrong_unit():
    val = 1 * u.T
    with pytest.raises(u.UnitConversionError):
        me.Ms(val, "T")


def test_wrong_quantity_with_equivalency():
    val = 1 * u.T
    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        me.Ms(val)


def test_wrong_quantity_with_equivalency_early_conversion():
    val = 1 * u.T
    with u.set_enabled_equivalencies(u.magnetic_flux_field()):
        e = me.Ms(val.to(u.A / u.m))
        assert u.allclose(e.quantity, val)
