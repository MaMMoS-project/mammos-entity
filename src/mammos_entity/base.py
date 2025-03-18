import abc

from astropy import units as u
from owlready2.entity import ThingClass

from mammos_entity.onto import mammos_ontology


class AbstractEntity(u.Quantity, abc.ABC):
    """
    An abstract base class representing a scalar physical entity.

    This class serves as a base for entities that have a single numeric value
    with specific physical units.

    :param quantity: The initial quantity with physical units.
    :type quantity: astropy.units.Quantity
    """

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        Initialize the scalar entity with a specified quantity.

        :param quantity: The initial quantity with physical units.
        :type quantity: astropy.units.Quantity
        """
        if self.unit not in list(self.si_units):
            raise TypeError(
                f"The units does not match the units of {self.ontology_label}"
            )

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
        return f"{self.ontology_label}(value={self.value}, unit={self.unit})"

    def __str__(self) -> str:
        return self.__repr__()

    def _repr_latex_(self) -> str:
        return f"{self.ontology_label}({super()._repr_latex_()})"
