import mammos_units as u

from mammos_entity.base import AbstractEntity


class Ms(AbstractEntity):
    """
    Represents the Spontaneous Magnetization (Mₛ).

    This is a scalar entity whose units are either A/m or T (tesla),
    corresponding to the magnetization.
    """

    def __new__(cls, value, unit=(u.A / u.m), **kwargs):
        unit = u.Unit(unit)
        if not unit.is_equivalent(u.A / u.m):
            raise TypeError(
                "The units does not match the units of Spontaneous Magnetization."
            )
        return super().__new__(cls, value, unit, **kwargs)

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for spontaneous magnetization.
        """
        return "SpontaneousMagnetization"


class A(AbstractEntity):
    """
    Represents the Exchange Stiffness Constant (A).

    This is a scalar entity whose units must be J/m (joules per meter).
    """

    def __new__(cls, value, unit=(u.J / u.m), **kwargs):
        unit = u.Unit(unit)
        if not unit.is_equivalent(u.J / u.m):
            raise TypeError(
                "The units does not match the units of Exchange Stiffness Constant."
            )
        return super().__new__(cls, value, unit, **kwargs)

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the exchange stiffness constant.
        """
        return "ExchangeStiffnessConstant"


class Ku(AbstractEntity):
    """
    Represents the Uniaxial Anisotropy Constant (Kᵤ).

    This is a vector entity whose magnitude’s units must be J/m³
    (joules per cubic meter), and whose direction is a normalized vector in space.
    """

    def __new__(cls, value, unit=(u.J / u.m**3), **kwargs):
        unit = u.Unit(unit)
        if not unit.is_equivalent(u.J / u.m**3):
            raise TypeError(
                "The units does not match the units of Uniaxial Anisotropy Constant."
            )
        return super().__new__(cls, value, unit, **kwargs)

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the uniaxial anisotropy constant.
        """
        return "UniaxialAnisotropyConstant"


class H(AbstractEntity):
    """
    Represents the External Magnetic Field (H).

    This is a vector entity whose magnitude’s units are either A/m or T (tesla),
    representing an external field applied to the material.
    """

    def __new__(cls, value, unit=(u.A / u.m), **kwargs):
        unit = u.Unit(unit)
        if not unit.is_equivalent(u.A / u.m):
            raise TypeError(
                "The units does not match the units of External Magnetic Field."
            )
        return super().__new__(cls, value, unit, **kwargs)

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the external magnetic field.
        """
        return "ExternalMagneticField"
