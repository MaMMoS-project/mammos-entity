"""Entity functionality.

Entities are quantities (numbers with units) with an associated ontology label.

This packages contains classes for defining, collecting and saving such entities (
:py:class:`~mammos_entity.Entity` and :py:class:`~mammos_entity.EntityCollection`),
the :py:func:`~mammos_entity.search_labels` function to search for partial
or full matches of labels defined in the ontology, the reading routines
:py:func:`~mammos_entity.from_csv`, :py:func:`~mammos_entity.from_hdf5`
:py:func:`~mammos_entity.from_yaml`, and some pre-defined factory methods for
magnetic entities (such as :py:class:`~mammos_entity.Ms`, :py:class:`~mammos_entity.A`,
:py:class:`~mammos_entity.Ku`, and :py:class:`~mammos_entity.H`).
"""

import importlib.metadata

from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection
from mammos_entity._factory import (
    K1,
    K2,
    A,
    B,
    BHmax,
    H,
    Hc,
    J,
    Js,
    Ku,
    M,
    Mr,
    Ms,
    T,
    Tc,
)
from mammos_entity._ontology import mammos_ontology, search_labels
from mammos_entity._read_files import from_csv, from_hdf5, from_yaml

from . import operations

__version__ = importlib.metadata.version(__package__)


__all__ = [
    "Entity",
    "EntityCollection",
    "A",
    "B",
    "BHmax",
    "H",
    "Hc",
    "J",
    "Js",
    "K1",
    "K2",
    "Ku",
    "M",
    "Mr",
    "Ms",
    "T",
    "Tc",
    "mammos_ontology",
    "operations",
    "search_labels",
    "units",
    "from_csv",
    "from_hdf5",
    "from_yaml",
]
