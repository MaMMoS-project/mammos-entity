from astropy import units as u
from mammos_entity.onto import mammos_ontology
from owlready2.entity import ThingClass
from typing import Sequence


class Ms:
    def __init__(self, quantity: u.Quantity):
        self.quantity = quantity

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity):
        if quantity.si.unit not in {(u.A / u.m), u.T}:
            raise TypeError(
                "The units of the quantity does not match the known units of Spontaneous Magnetisation."
            )
        else:
            self._quantity = quantity

    @property
    def ontology(self) -> ThingClass:
        return mammos_ontology.get_by_label("SpontaneousMagnetization")

    def __repr__(self):
        return f"Spontaneous Magnetization (value={self.quantity.value}, unit={self.quantity.unit})"


class A:
    def __init__(self, quantity: u.Quantity):
        self.quantity = quantity

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity):
        if quantity.si.unit != (u.J / u.m):
            raise TypeError(
                "The units of the quantity does not match the known units of Exchange Stiffness Constant."
            )
        else:
            self._quantity = quantity

    @property
    def ontology(self) -> ThingClass:
        return mammos_ontology.get_by_label("ExchangeStiffnessConstant")

    def __repr__(self):
        return f"Exchange Stiffness Constant (value={self.quantity.value}, unit={self.quantity.unit})"


class Ku:
    def __init__(self, quantity: u.Quantity, direction: Sequence[[float, int]]):
        self.quantity = quantity
        self.direction = direction

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity):
        if quantity.si.unit != (u.J / u.m**3):
            raise TypeError(
                "The units of the quantity does not match the known units of Uniaxial Anisotropy Constant."
            )
        else:
            self._quantity = quantity

    @property
    def ontology(self) -> ThingClass:
        return mammos_ontology.get_by_label("UniaxialAnisotropyConstant")

    def __repr__(self):
        return f"Uniaxial Anisotropy Constant (value={self.quantity.value}, unit={self.quantity.unit}, direction={self.direction})"


class H:
    def __init__(self, quantity: u.Quantity, direction: Sequence[[float, int]]):
        self.quantity = quantity
        self.direction = direction

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, quantity):
        if quantity.si.unit not in {(u.A / u.m), u.T}:
            raise TypeError(
                "The units of the quantity does not match the known units of External Magnetic Field."
            )
        else:
            self._quantity = quantity

    @property
    def ontology(self) -> ThingClass:
        return mammos_ontology.get_by_label("ExternalMagneticField")

    def __repr__(self):
        return f"External Magnetic Field (value={self.quantity.value}, unit={self.quantity.unit}, direction={self.direction})"
