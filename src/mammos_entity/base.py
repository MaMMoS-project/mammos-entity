import abc
import collections
from typing import Sequence

import numpy as np
from astropy import units as u
from owlready2.entity import ThingClass

from mammos_entity.onto import mammos_ontology


class AbstractScalarEntity(abc.ABC):
    """
    An abstract base class representing a scalar physical entity.

    This class serves as a base for entities that have a single numeric value
    with specific physical units. The quantity is enforced through an abstract property
    and must be validated by subclasses.

    :param quantity: The initial quantity with physical units.
    :type quantity: astropy.units.Quantity
    """

    def __init__(self, quantity: u.Quantity):
        """
        Initialize the scalar entity with a specified quantity.

        :param quantity: The initial quantity with physical units.
        :type quantity: astropy.units.Quantity
        """
        self.quantity = quantity

    @property
    @abc.abstractmethod
    def ontology_label(self) -> str:
        """
        str: The ontology label that identifies the underlying concept for this entity.

        Each subclass should provide an ontology label that uniquely identifies the
        concept.
        """
        pass

    @property
    @abc.abstractclassmethod
    def si_units(self) -> set[u.Unit]:
        """
        set[astropy.units.Unit]: The collection of SI units against which the units of
        the quantity are checked at assignment.

        Each subclass should provide a set of SI units corresponding to the entity.
        """
        pass

    @property
    def quantity(self) -> u.Quantity:
        """
        Get the entity’s scalar quantity.

        :return: The scalar quantity of this entity.
        :rtype: astropy.units.Quantity
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: u.Quantity):
        """
        Validate and set the quantity value.

        :param quantity: The quantity corresponding to the entity.
        :type quantity: astropy.units.Quantity
        :raises TypeError: If the unit is not in the `si_units` property.
        """
        if quantity.si.unit not in list(self.si_units):
            raise TypeError(
                f"The units does not match the units of {self.ontology_label}"
            )
        else:
            self._quantity = quantity

    @property
    def ontology(self) -> ThingClass:
        """
        owlready2.entity.ThingClass: The associated ontology class object.

        Uses the ontology label to fetch the corresponding class from `mammos_ontology`.
        """
        return mammos_ontology.get_by_label(self.ontology_label)

    def __repr__(self) -> str:
        """
        Return a string representation of the entity, showing the label,
        numeric value, and unit.

        :return: String representation of the entity.
        :rtype: str
        """
        return f"{self.ontology_label}(value={self.quantity.value}, unit={self.quantity.unit})"


class AbstractVectorEntity(AbstractScalarEntity):
    """
    An abstract class for vector physical entities.

    In addition to a scalar magnitude (`quantity`), this entity includes a direction
    stored as a normalized vector. Subclasses are expected to ensure proper unit
    validation of the magnitude.
    """

    def __init__(self, quantity: u.Quantity, direction: Sequence[[float, int]]):
        """
        Initialize a vector entity with a scalar quantity and a direction.

        :param quantity: The magnitude of the vector with physical units.
        :type quantity: astropy.units.Quantity
        :param direction: The components of the direction as a sequence of floats.
        :type direction: Sequence[[float, int]]

        :raises TypeError: If the direction is not a sequence.
        :raises ValueError: If the direction has a zero or invalid norm.
        """
        super().__init__(quantity=quantity)
        self.direction = direction

    @property
    def direction(self) -> np.ndarray:
        """
        numpy.ndarray: The direction vector (normalized) representing the orientation
        of the entity in space.
        """
        return self._direction

    @direction.setter
    def direction(self, direction: Sequence[[float, int]]):
        """
        Set the direction vector and normalize it.

        :raises TypeError: If the provided direction is not a sequence.
        """
        if not isinstance(direction, collections.abc.Sequence):
            raise TypeError("The direction must be a sequence.")
        else:
            self._direction = np.array(direction) / np.linalg.norm(direction)

    def __repr__(self) -> str:
        """
        Return a string representation of the entity, including the scalar quantity
        and the direction vector.

        :return: String representation of the entity.
        :rtype: str
        """
        return super().__repr__()[:-1] + f", direction={self.direction})"
