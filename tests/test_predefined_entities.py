import mammos_units as u
import pytest

import mammos_entity as me


def test_Ms_unit_val():
    e = me.Ms(42)
    assert e.unit == (u.A / u.m)


def test_Ms_unit_allowed():
    allowed_units = ["A/m", "mA/m", "kA/m", "nA/m", "MA/m"]
    for unit in allowed_units:
        _ = me.Ms(42, unit)


def test_Ms_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(TypeError):
            _ = me.Ms(42, unit)


def test_Ms_ontology():
    e = me.Ms(42)
    assert str(e.ontology.prefLabel[0]) == "SpontaneousMagnetization"


def test_A_unit_val():
    e = me.A(42)
    assert e.unit == (u.J / u.m)


def test_A_unit_allowed():
    allowed_units = ["J/m", "mJ/m", "kJ/m", "nJ/m", "MJ/m"]
    for unit in allowed_units:
        _ = me.A(42, unit)


def test_A_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(TypeError):
            _ = me.A(42, unit)


def test_A_ontology():
    e = me.A(42)
    assert str(e.ontology.prefLabel[0]) == "ExchangeStiffnessConstant"


def test_Ku_unit_val():
    e = me.Ku(42)
    assert e.unit == (u.J / u.m**3)


def test_Ku_unit_allowed():
    allowed_units = ["J/m3", "mJ/m3", "kJ/m3", "nJ/m3", "MJ/m3"]
    for unit in allowed_units:
        _ = me.Ku(42, unit)


def test_Ku_unit_not_allowed():
    unallowed_units = ["T", "A", "J/m2", "m"]
    for unit in unallowed_units:
        with pytest.raises(TypeError):
            _ = me.Ku(42, unit)


def test_Ku_ontology():
    e = me.Ku(42)
    assert str(e.ontology.prefLabel[0]) == "UniaxialAnisotropyConstant"


def test_H_unit_val():
    e = me.H(42)
    assert e.unit == (u.A / u.m)


def test_H_unit_allowed():
    allowed_units = ["A/m", "mA/m", "kA/m", "nA/m", "MA/m"]
    for unit in allowed_units:
        _ = me.H(42, unit)


def test_H_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(TypeError):
            _ = me.H(42, unit)


def test_H_ontology():
    e = me.H(42)
    assert str(e.ontology.prefLabel[0]) == "ExternalMagneticField"


def test_unique_labels():
    assert len({me.A().label, me.Ms().label, me.Ku().label, me.H().label}) == 4
