"""Entity functionality.

Entities are quantities (numbers with units) with an associated ontology label.

This packages contains classes for defining, collecting and saving such entities (
:py:class:`~mammos_entity.Entity` and :py:class:`~mammos_entity.EntityCollection`)
from specific ontologies (:py:class:`~mammos_entity.Ontology`) defining the meaning
and the context of each object. The object `mammos_ontology` is initialized as an
:py:class:`~mammos_entity.Ontology` representing the EMMO-base `magnetic materials domain
ontology (MagMO) <https://emmo-repo.github.io/domain-magnetic-materials/>`__.

The function :py:func:`~mammos_entity.search_labels` can be used to search for partial
or full matches of labels defined in MagMO, while the reading routines
:py:func:`~mammos_entity.from_csv`, :py:func:`~mammos_entity.from_hdf5`, and
:py:func:`~mammos_entity.from_yaml` define :py:class:`~mammos_entity.EntityCollection`
objects from `mammos` files.

Furthermore, some pre-defined factory methods for magnetic entities are present, such as
general terms (e.g. magnetization :py:class:`~mammos_entity.M` and temperature
:py:class:`~mammos_entity.T`), magnetic intrinsic properties (e.g. spontaneous magnetization
:py:class:`~mammos_entity.Ms`), magnetic extrinsic properties (e.g. remanent magnetization
:py:class:`~mammos_entity.Mr`), and other magnetic quantities (e.g. Curie temperature
:py:class:`~mammos_entity.Tc`).
)
"""

import importlib.metadata

from platformdirs import user_cache_path

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
from mammos_entity._ontology import Ontology, mammos_ontology, search_labels
from mammos_entity._read_files import from_csv, from_hdf5, from_yaml

from . import _io, operations

__version__ = importlib.metadata.version(__package__)


__all__ = [
    "_io",
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
    "Ontology",
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


(_CACHE_DIR := user_cache_path("mammos_entity", ensure_exists=True))
