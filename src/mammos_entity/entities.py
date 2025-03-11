from astropy import units as u

from mammos_entity.base import AbstractScalarEntity, AbstractVectorEntity


class Ms(AbstractScalarEntity):
    """
    Represents the Spontaneous Magnetization (Mₛ).

    This is a scalar entity whose units are either A/m or T (tesla),
    corresponding to the magnetization.
    """

    @property
    def quantity(self) -> u.Quantity:
        """
        Get the spontaneous magnetization value.

        :return: The magnetization quantity.
        :rtype: astropy.units.Quantity
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: u.Quantity):
        """
        Validate and set the spontaneous magnetization value.

        :param quantity: The magnetization quantity (A/m or T).
        :type quantity: astropy.units.Quantity
        :raises TypeError: If the unit is not compatible with A/m or T.
        """
        if (quantity.si.unit != (u.A / u.m)) and (quantity.si.unit != u.T):
            raise TypeError(
                "The units does not match the units of Spontaneous Magnetisation."
            )
        else:
            self._quantity = quantity

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for spontaneous magnetization.
        """
        return "SpontaneousMagnetization"


class A(AbstractScalarEntity):
    """
    Represents the Exchange Stiffness Constant (A).

    This is a scalar entity whose units must be J/m (joules per meter).
    """

    @property
    def quantity(self) -> u.Quantity:
        """
        Get the exchange stiffness constant value.

        :return: The exchange stiffness constant (J/m).
        :rtype: astropy.units.Quantity
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: u.Quantity):
        """
        Validate and set the exchange stiffness constant value.

        :param quantity: The exchange stiffness constant (J/m).
        :type quantity: astropy.units.Quantity
        :raises TypeError: If the unit is not J/m.
        """
        if quantity.si.unit != (u.J / u.m):
            raise TypeError(
                "The units does not match the units of Exchange Stiffness Constant."
            )
        else:
            self._quantity = quantity

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the exchange stiffness constant.
        """
        return "ExchangeStiffnessConstant"


class Ku(AbstractVectorEntity):
    """
    Represents the Uniaxial Anisotropy Constant (Kᵤ).

    This is a vector entity whose magnitude’s units must be J/m³
    (joules per cubic meter), and whose direction is a normalized vector in space.
    """

    @property
    def quantity(self) -> u.Quantity:
        """
        Get the uniaxial anisotropy constant's magnitude.

        :return: The anisotropy constant quantity (J/m³).
        :rtype: astropy.units.Quantity
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: u.Quantity):
        """
        Validate and set the uniaxial anisotropy constant's magnitude.

        :param quantity: The anisotropy constant (J/m³).
        :type quantity: astropy.units.Quantity
        :raises TypeError: If the unit is not J/m³.
        """
        if quantity.si.unit != (u.J / u.m**3):
            raise TypeError(
                "The units does not match the units of Uniaxial Anisotropy Constant."
            )
        else:
            self._quantity = quantity

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the uniaxial anisotropy constant.
        """
        return "UniaxialAnisotropyConstant"


class H(AbstractVectorEntity):
    """
    Represents the External Magnetic Field (H).

    This is a vector entity whose magnitude’s units are either A/m or T (tesla),
    representing an external field applied to the material.
    """

    @property
    def quantity(self) -> u.Quantity:
        """
        Get the external magnetic field's magnitude.

        :return: The external magnetic field quantity.
        :rtype: astropy.units.Quantity
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: u.Quantity):
        """
        Validate and set the external magnetic field's magnitude.

        :param quantity: The magnetic field quantity (A/m or T).
        :type quantity: astropy.units.Quantity
        :raises TypeError: If the unit is not compatible with A/m or T.
        """
        if (quantity.si.unit != (u.A / u.m)) and (quantity.si.unit != u.T):
            raise TypeError(
                "The units does not match the units of External Magnetic Field."
            )
        else:
            self._quantity = quantity

    @property
    def ontology_label(self) -> str:
        """
        str: The ontology label for the external magnetic field.
        """
        return "ExternalMagneticField"
