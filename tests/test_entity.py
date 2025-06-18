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


# various tests to check different numpy functions:
# - return an entity if the meaning of the data has not changed and the units match
# - return a quantity if something has changed (or if there is possible ambiguity)
# type checks via `type(...) is ...` to ensure we check for exact type (not subclasses)


def test_numpy_squeeze():
    inp = me.Ms([[1, 1]])
    out = np.squeeze(inp)
    assert type(out) is me.Entity
    assert out.ontology_label == inp.ontology_label
    assert out.shape == (2,)
    np.testing.assert_allclose(out.value, [1, 1])


def test_numpy_power():
    inp = me.Ms(3)
    out = np.power(inp, 2)
    assert type(out) is u.Quantity
    np.testing.assert_allclose(out.value, 9)


def test_numpy_ones_like():
    inp = me.Ms(3)
    out = np.ones_like(inp)
    assert type(out) is me.Entity
    assert out.ontology_label == inp.ontology_label
    assert out.shape == ()
    np.testing.assert_allclose(out.value, 1)


def test_getitem():
    inp = me.Ms([1, 2, 3])
    out = inp[:]
    assert type(out) is me.Entity
    assert out.ontology_label == inp.onology_label
    np.testing.assert_allclose(inp, out)

    out = inp[[True, False, True]]
    assert type(out) is me.Entity
    assert out.ontology_label == inp.onology_label
    np.testing.assert_allclose(inp, [1, 3])

    out = inp[1]
    assert type(out) is me.Entity
    assert out.ontology_label == inp.onology_label
    np.testing.assert_allclose(inp, 2)


def test_np_positive():
    inp = me.Ms(-100)
    out = np.positive(inp)
    assert type(out) is u.Quantity


def test_isnan():
    inp = me.Ms()
    assert not np.isnan(inp)


def test_to_string():
    with pytest.raises(AttributeError):
        me.Ms().to_string()


def test_multiplication_with_number():
    inp = me.Ms(1)
    out = inp * 3
    assert type(out) is u.Quantity
    np.testing.assert_allclose(out.value, 3)


def test_multiplication_with_unit():
    inp = me.Ms(1)
    out = inp * u.K
    assert type(out) is u.Quantity
    assert out.unit == "K A / m"


def test_np_insert():
    inp = me.Ms([1, 2])
    out = inp.insert(0, 3 * u.A / u.m)
    assert type(out) is me.Entity
    assert out.ontology_label == inp.onology_label
    np.testing.assert_allclose(inp.value, [3, 1, 2])


def test_np_mean():
    inp = me.Ms([1, 3])
    out = np.mean(inp)
    assert type(out) is u.Quantity
    np.testing.assert_allclose(out.value, 2)


def test_np_linalg_norm():
    inp = me.Ms([3, 4])
    out = np.linalg.norm(inp)
    assert type(out) is u.Quantity
    np.testing.assert_allclose(out.value, 5)


def test_decompose():
    inp = me.B()
    out = inp.decompose()
    assert type(out) is me.Entity
    assert out.ontology_label == inp.ontology_label
    assert out.unit == "kg / (A s2)"


def test_lshift():
    # unit conversion in astropy, implementation not well suited for subclassing
    inp = me.B()
    out = inp << u.mT
    assert type(out) is me.Entity
    assert out.ontology_label == inp.ontology_label

    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        inp << u.A / u.m  # not compatible with ontology


def test_ilshift():
    val = me.B()
    ontology_label = val.ontology_label
    val <<= u.mT
    assert type(val) is me.Entity
    assert val.ontology_label == ontology_label

    with (
        u.set_enabled_equivalencies(u.magnetic_flux_field()),
        pytest.raises(u.UnitConversionError),
    ):
        val <<= u.A / u.m  # not compatible with ontology
