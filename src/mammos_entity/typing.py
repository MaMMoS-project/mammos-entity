"""Custom types in mammos_entity."""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

import mammos_units as u
import numpy.typing as npt

import mammos_entity as me

_OntologyLabelT = TypeVar("_OntologyLabelT", bound=str)


class EntityLike(Generic[_OntologyLabelT]):
    """Generic type for objects that can be interpreted as a specific entity.

    This class can be used to type annotate arguments that can take objects of different
    types that can be interpreted as instances of a specific element of the ontology.
    ``EntityLike["ontology_label"]`` are the following objects:

    - :py:class:`~mammos_entity.Entity` instances if the ontology label is correct, i.e.
      :py:class:`mammos_entity.Entity["ontology_label"] <mammos_entity.Entity>`
    - :py:class:`~astropy.units.Quantity` instances if the units are compatible with the
      ontology. The quantity is interpreted as the requested ontology element.
    - :py:class:`numpy.typing.ArrayLike` without further constraints. The data is
      interpreted as the requested ontology element in the default ontology unit.

    At runtime the ``ontology_label`` is available in the metadata of ``Annotated``.

    .. note::

       This class cannot be instantiated.

    """

    def __class_getitem__(cls, ontology_label: str):
        """EntityLike type hints with ontology label.

        Args:
            ontology_label: Label defined in the ontology.

        Returns:
            Annotated object with ontology label as metadata.

        Raises:
            TypeError: If the `ontology_label` is not of type str.
            ontopy.utils.NoSuchLabelError: If the `ontology_label` cannot be found in
                the ontology. Checks for presence in the ontology are performed with
                :py:func:`mammos_entity.mammos_ontology.get_by_label`.


        Examples:
            >>> from mammos_entity.typing import EntityLike
            >>> EntityLike["SpontaneousMagnetization"]
            typing.Annotated[typing.Union[mammos_entity._base.Entity, ...], 'SpontaneousMagnetization']

        """  # noqa: E501  # ignore long lines: to keep the example nicely formatted
        if not isinstance(ontology_label, str):
            raise TypeError("EntityLike[...] needs a literal str label.")

        # check that ontology_label exists in the ontology
        me.mammos_ontology.get_by_label(ontology_label)

        # ArrayLike contains Quantity; added explicitly to stress that Quantity allowed
        return Annotated[me.Entity | u.Quantity | npt.ArrayLike, ontology_label]

    def __new__(cls, *args, **kwargs):  # noqa: D102  # ignore missing docstring
        raise TypeError("Type EntityLike cannot be instantiated.")
