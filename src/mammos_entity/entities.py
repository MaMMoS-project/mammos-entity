from astropy import units as u

from mammos_entity.base import AbstractEntity


class Ms(AbstractEntity):
    """
    Represents the Spontaneous Magnetization (Mₛ).

    This is a scalar entity whose units are either A/m or T (tesla),
    corresponding to the magnetization.
    """

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for spontaneous magnetization.
        """
        return "SpontaneousMagnetization"

    @property
    def si_units(self) -> set[u.Unit]:
        """
        set[astropy.units.Unit]: SI units for spontaneous magnetization, A/m and T.
        """
        return {(u.A / u.m), u.T}


class A(AbstractEntity):
    """
    Represents the Exchange Stiffness Constant (A).

    This is a scalar entity whose units must be J/m (joules per meter).
    """

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the exchange stiffness constant.
        """
        return "ExchangeStiffnessConstant"

    @property
    def si_units(self) -> set[u.Unit]:
        """
        set[astropy.units.Unit]: SI units for exchange stiffness constant, J/m.
        """
        return {u.J / u.m}


class Ku(AbstractEntity):
    """
    Represents the Uniaxial Anisotropy Constant (Kᵤ).

    This is a vector entity whose magnitude’s units must be J/m³
    (joules per cubic meter), and whose direction is a normalized vector in space.
    """

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the uniaxial anisotropy constant.
        """
        return "UniaxialAnisotropyConstant"

    @property
    def si_units(self) -> set[u.Unit]:
        """
        set[astropy.units.Unit]: SI units for uniaxial anisotropy constant, J/m³.
        """
        return {u.J / u.m**3}


class H(AbstractEntity):
    """
    Represents the External Magnetic Field (H).

    This is a vector entity whose magnitude’s units are either A/m or T (tesla),
    representing an external field applied to the material.
    """

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the external magnetic field.
        """
        return "ExternalMagneticField"

    @property
    def si_units(self) -> set[u.Unit]:
        """
        set[astropy.units.Unit]: SI units for external magnetic field, A/m and T.
        """
        return {(u.A / u.m), u.T}
