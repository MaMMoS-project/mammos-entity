"""Reading function for HDF5 v2.

The HDF5 structure is interpreted as follows:

- HDF5 groups are converted to :py:class:`~mammos_entity.EntityCollection`.
  The group's ``description`` attribute (if present) becomes the collection
  description. All other group attributes are ignored.
- Nested groups produce nested :py:class:`~mammos_entity.EntityCollection`
  objects.
- HDF5 datasets are converted depending on their attributes:

  * If the dataset has all of the attributes ``ontology_label``,
    ``ontology_iri``, ``entity_iri``, ``description`` and ``unit``,
    it is converted to an :py:class:`~mammos_entity.Entity`.
  * If the dataset has only a ``unit`` attribute (but not the ontology-related
    attributes), it is converted to a :py:class:`~mammos_units.Quantity`.
  * Otherwise the dataset is returned as a numpy array, a scalar, or a string
    (the exact type is inherited from h5py).
- All other HDF5 attributes are silently ignored.
- The ``decode_bytes`` parameter controls whether byte-string datasets are
  decoded to Python strings.

This means external HDF5 files (not written by mammos-entity) can be read
as long as their groups and datasets follow the attribute naming conventions
listed above.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import h5py
import mammos_units as u

import mammos_entity as me

if TYPE_CHECKING:
    import mammos_units
    import numpy

    import mammos_entity


def _from_hdf5_v2(
    element: h5py.File | h5py.Group | h5py.Dataset,
    decode_bytes: bool = True,
    ontologies: dict | None = None,
) -> mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike | mammos_entity.EntityCollection:
    """Read HDF5 file, group or dataset and convert to Entity or EntityCollection.

    Args:
        element: Part of the file that is read.
        decode_bytes: If ``True`` data of all datasets of type object is converted to
            strings (if scalar) or numpy arrays of strings (if vector). If ``False`` the
            bytes object (or array of bytes objects) is returned.
        ontologies: dictionary of needed ontologies. While this will start as an empty
            dictionary, the recursive call will populate it step by step.

    Returns:
        All data in the given HDF5 file/group/dataset as (nested) EntityCollection
        and/or entity-like object.

    .. seealso::

       :py:func:`mammos_entity.Entity.to_hdf5`
       :py:func:`mammos_entity.EntityCollection.to_hdf5`
    """
    if ontologies is None:
        ontologies = {}
    if isinstance(element, h5py.File | h5py.Group):
        collection = me.EntityCollection(description=element.attrs.get("description", ""))
        for name, sub in element.items():
            collection[name] = _from_hdf5_v2(sub, ontologies=ontologies)
        return collection
    elif "ontology_label" in element.attrs:
        # if the entity belongs to an ontology used before, we use it from
        # the `ontologies` dictionary. Otherwise, we initialize an ontology
        # with such iri and we use it to define the entity.
        ontology_iri = element.attrs["ontology_iri"]
        ontology = ontologies.get(ontology_iri, me.Ontology([ontology_iri], initialize=True))
        return me.Entity(
            ontology_label=element.attrs["ontology_label"],
            value=element[()],
            unit=element.attrs["unit"],
            iri=element.attrs["entity_iri"],
            description=element.attrs["description"],
            ontology=ontology,
        )
    elif "unit" in element.attrs:
        return u.Quantity(element[()], element.attrs["unit"])
    else:
        if element.dtype == "object" and decode_bytes:
            element = element.asstr()
        data = element[()]
        return data
