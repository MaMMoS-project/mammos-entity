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
        with pytest.raises(u.UnitConversionError):
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
        with pytest.raises(u.UnitConversionError):
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
        with pytest.raises(u.UnitConversionError):
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
        with pytest.raises(u.UnitConversionError):
            _ = me.H(42, unit)


def test_H_ontology():
    e = me.H(42)
    assert str(e.ontology.prefLabel[0]) == "ExternalMagneticField"


def test_J_ontology():
    J = me.J(1)
    assert str(J.ontology.prefLabel[0]) == "MagneticPolarisation"


def test_Js_ontology():
    Js = me.Js(1)
    assert str(Js.ontology.prefLabel[0]) == "SpontaneousMagneticPolarisation"


def test_Tc_unit_val():
    e = me.Tc(42)
    assert e.unit == u.K


def test_Tc_unit_allowed():
    allowed_units = ["K", "mK", "kK", "nK", "MK"]
    for unit in allowed_units:
        _ = me.Tc(42, unit)


def test_Tc_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m", "deg_C"]
    for unit in unallowed_units:
        with pytest.raises(u.UnitConversionError):
            _ = me.Tc(42, unit)


def test_Tc_ontology():
    e = me.Tc(42)
    assert str(e.ontology.prefLabel[0]) == "CurieTemperature"


def test_Hc_unit_val():
    e = me.Hc(42)
    assert e.unit == (u.A / u.m)


def test_Hc_unit_allowed():
    allowed_units = ["A/m", "mA/m", "kA/m", "nA/m", "MA/m"]
    for unit in allowed_units:
        _ = me.Hc(42, unit)


def test_Hc_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(u.UnitConversionError):
            _ = me.Hc(42, unit)


def test_Hc_ontology():
    e = me.Hc(42)
    assert str(e.ontology.prefLabel[0]) == "CoercivityHcExternal"


def test_Mr_unit_val():
    e = me.Mr(42)
    assert e.unit == (u.A / u.m)


def test_Mr_unit_allowed():
    allowed_units = ["A/m", "mA/m", "kA/m", "nA/m", "MA/m"]
    for unit in allowed_units:
        _ = me.Mr(42, unit)


def test_Mr_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(u.UnitConversionError):
            _ = me.Mr(42, unit)


def test_Mr_ontology():
    e = me.Mr(42)
    assert str(e.ontology.prefLabel[0]) == "Remanence"


def test_BHmax_unit_not_allowedval():
    e = me.BHmax(42)
    assert e.unit == (u.J / u.m**3)


def test_BHmax_unit_allowed():
    allowed_units = ["J/m3", "mJ/m3", "kJ/m3", "nJ/m3", "MJ/m3"]
    for unit in allowed_units:
        _ = me.BHmax(42, unit)


def test_BHmax_unit_not_allowed():
    unallowed_units = ["T", "A", "J", "m"]
    for unit in unallowed_units:
        with pytest.raises(u.UnitConversionError):
            _ = me.BHmax(42, unit)


def test_BHmax_ontology():
    e = me.BHmax(42)
    assert str(e.ontology.prefLabel[0]) == "MaximumEnergyProduct"


def test_unique_labels():
    # hard coded version for clarity
    assert (
        len(
            {
                me.A().ontology_label,
                me.BHmax().ontology_label,
                me.H().ontology_label,
                me.Hc().ontology_label,
                me.M().ontology_label,
                me.Ms().ontology_label,
                me.Ku().ontology_label,
                me.Tc().ontology_label,
                me.Mr().ontology_label,
            }
        )
        == 9
    )
    # check entities automatically
    names = [name for name in dir(me) if not name.startswith("_")]
    # names.remove('mammos_ontology')

    # do we have ontology_label, and are they unique?
    assert len(names) == len(set(names))


def test_ontology_label():
    Ms = me.Ms(8e5, "A/m")
    assert Ms.ontology_label == "SpontaneousMagnetization"


def test_ontology_label_with_iri():
    Ms = me.Ms(8e5, "A/m")
    assert (
        Ms.ontology_label_with_iri
        == "SpontaneousMagnetization https://w3id.org/emmo/domain/magnetic_material#EMMO_032731f8-874d-5efb-9c9d-6dafaa17ef25"
    )
