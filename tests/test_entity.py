import numpy as np
import pytest

import mammos_entity as me


def test_unit_conversion():
    e = me.A(42)  # NOTE: we know that unit by default J/m
    e_same = me.A(42e3, unit="mJ/m")
    assert np.allclose(e, e_same)  # NOTE: entities are essentually numpy arrays!


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
