"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology, including
everything from the EMMO ontology, via the `EMMOntoPy` library. The ontology is loaded
from ``.ttl`` (Turtle) files distributed with mammos-entity.
"""

from __future__ import annotations

import os
import re
import warnings
from collections.abc import Iterable
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

import ontopy
import requests
import urllib3

import mammos_entity as me
from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection

logger = getLogger(__package__)

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing
    import ontopy.ontology

    import mammos_entity


class Ontology:
    """TODO: docstring.

    Attrs:
        iris: list of ``versionIRI`` urls of all loaded ontology. Each ontology
            will be automatically downloaded in the cache for future use.

    .. version-added: 0.14.0
       The Ontology class.
    """

    def __init__(self, iris: Iterable[str] | None = None, initialize: bool = False):
        """TODO: docstring."""
        if iris is None:
            self._iris = ["https://w3id.org/emmo/domain/magnetic-materials/0.0.6/inferred"]
        else:
            self._iris = list(iris)
        self._initialized = False
        self._ontopy_ontology = None
        if initialize:
            self.initialize()

    def __str__(self):
        """TODO: docstring."""
        _init = " (initialized)" if self._initialized else ""
        out = f"Ontology:{_init}\n"
        if self._iris is None:
            out += "- local `magmo`."
        else:
            out += "\n".join(f"- {iri}" for iri in self._iris)
        return out

    def __repr__(self):
        """TODO: docstring."""
        arg = f"{self._iris!r}" if self._iris else ""
        return f"Ontology({arg})"

    @property
    def iris(self) -> list[str]:
        """TODO: docstring."""
        return self._iris

    @iris.setter
    def iris(self, _) -> None:
        """TODO: docstring."""
        raise RuntimeError(
            "Do not assign the iris directly. To add new iris, use the method "
            "`add`. To remove iris, please initiate a new `Ontology` object."
        )

    def initialize(self, use_cache: bool = True):
        """TODO: docstring."""
        if self._initialized:
            warnings.warn(
                "Already initialized. Re-initializing.",
                stacklevel=1,
            )
        self._ontopy_ontology = _load_ontologies(self.iris, use_cache=use_cache)
        self._initialized = True

    def add_iri(self, iri: str):
        """TODO. docstring."""
        if iri in self._iris:
            warnings.warn(
                f"IRI: '{iri}' was already in the list: {self.iris!s}.",
                stacklevel=1,
            )
        else:
            if self._initialized:
                new_dep = self._ontopy_ontology.world.get_ontology(iri).load()
                self._ontopy_ontology.imported_ontologies.append(new_dep)
            self._iris.append(iri)

    def search_labels(self, text: str, auto_wildcard: bool = True) -> list[str]:
        """Search entity labels by name.

        TODO: update.

        The string ``text`` is searched into ``label``, ``prefLabel``, and ``altLabel`` of
        all entities. The match is case sensitive. The returned label is always the
        ``prefLabel``.

        This function uses internally the method ``.search()`` of
        ``mammos_entity.mammos_ontology``.

        Args:
            text: String to match.
            auto_wildcard: If True, the wildcard ``*`` is added at the beginning
                and at the end of the string ``text``. This allows partial matches, finding
                labels containing ``text``. If False, only labels identical to ``text``
                are returned.

                Passing ``"text", auto_wildcard=True`` is identical to passing
                ``"*text*", auto_wildcard=False``.

        Examples:
            >>> import mammos_entity as me
            >>> me.search_labels("ShapeAnisotropy")
            ['ShapeAnisotropy', 'ShapeAnisotropyConstant']

            >>> me.search_labels("Magnetization")
            ['MagneticMomentPerUnitMass', 'Magnetization', 'MassMagnetizationUnit', 'Remanence', 'SaturationMagnetization', 'SpontaneousMagnetization']

            ``'MagneticMomentPerUnitMass'`` appears because ``'MassMagnetization'`` is
            in its ``altLabel``.

            >>> me.search_labels("Magnetization", auto_wildcard=False)
            ['Magnetization']

        """  # noqa:E501
        label = f"*{text}*" if auto_wildcard else text
        match_by_label = set(self._ontopy_ontology.search(label=label))
        match_by_prefLabel = set(self._ontopy_ontology.search(prefLabel=label))
        match_by_altLabel = set(self._ontopy_ontology.search(altLabel=label))
        possible_things = match_by_label | match_by_prefLabel | match_by_altLabel
        return sorted(str(thing.prefLabel[0]) for thing in possible_things if hasattr(thing, "prefLabel"))

    def Entity(
        self,
        ontology_label: str = "",
        value: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike = 0,
        unit: str | None | mammos_units.UnitBase = None,
        *,
        iri: str = "",
        description: str = "",
    ):
        """TODO: docstring."""
        if not self._initialized:
            self.initialize()
        return Entity(ontology_label, value, unit, iri=iri, description=description, ontology=self)

    def EntityCollection(
        self,
        description: str = "",
        **kwargs: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike,
    ):
        """TODO: docstring."""
        if not self._initialized:
            self.initialize()
        return EntityCollection(description=description, ontology=self, **kwargs)


def _iri_to_filename(iri: str) -> os.PathLike:
    """TODO: docstring."""
    name, version = _iri_to_info(iri)
    return me._CACHE_DIR / name / version / "inferred.ttl"


def _iri_to_inferred(iri: str) -> os.PathLike:
    """TODO: docstring."""
    emmo_domain = "https://w3id.org/emmo"
    name, version = _iri_to_info(iri)
    if name == "emmo":
        return f"{emmo_domain}/{version}/inferred"
    else:
        if name == "magnetic-materials":
            return f"{emmo_domain}/domain/{name}/inferred"  # HACK: MagMO versionIRI does not work
        return f"{emmo_domain}/domain/{name}/{version}/inferred"


def _iri_to_info(iri: str) -> tuple(str):
    """TODO: docstring."""
    if "https://w3id.org/emmo" not in iri:
        raise ValueError(f"Not an EMMO iri. Given iri: {iri}.")
    emmo_domain = "https://w3id.org/emmo/"
    onto_info = iri.replace(emmo_domain, "")
    version = re.search(r"\d+.\d+.\d+", onto_info).group()
    name = re.search(r".*\d+.\d+.\d+", onto_info).group()
    if name == version:
        return ("emmo", version)
    else:
        return (name.replace("domain/", "").replace(f"/{version}", ""), version)


def _load_local_ontologies(verbose: bool = False) -> (ontopy.ontology.Ontology, list[str]):
    """Load EMMO and MaMMoS ontology from 'ontology' directory.

    The returned ontology object contains all definitions from both ontologies, EMMO is
    in the attribute ``.imported_ontologies`` and accessible in other methods when using
    ``imported=True``.

    """
    world = ontopy.World()
    ontology_dir = (Path(__file__).parent / "ontology").resolve()
    # load EMMO
    # using pathlib.Path(...).as_uri() causes ontopy to fail on Windows, therefore
    # we construct the file uri manually in the form required for ontopy
    emmo_ttl = f"file://{ontology_dir / 'emmo-inferred.ttl'!s}"
    logger.debug("loading emmo ttl from '%s'", emmo_ttl)
    emmo = world.get_ontology(emmo_ttl).load()
    iris = [emmo.get_version(as_iri=True)]
    # now load MaMMoS ontology, which builds upon EMMO; with EMMO already loaded
    # no internet access is required to resolve 'owl:imports <https://w3id.org/emmo'
    mammos_ttl = f"file://{ontology_dir / 'magnetic-materials.ttl'!s}"
    logger.debug("loading mammos ttl from '%s'", mammos_ttl)
    onto = world.get_ontology(mammos_ttl).load()
    iris.append(onto.get_version(as_iri=True))
    return onto, iris


def _load_online_ontologies(iris: Iterable[str], verbose: bool = False) -> ontopy.ontology.Ontology:
    """Fetch EMMO and MaMMoS ontology from the internet.

    TODO: update.
    """
    world = ontopy.World()
    onto = world.get_ontology("ontology")
    for iri in iris:
        if verbose:
            print(f"Reading {iri}")
        dep = world.get_ontology(iri).load()
        onto.imported_ontologies.append(dep)
    return onto


def _load_ontologies(iris: Iterable[str], use_cache: bool = True) -> ontopy.ontology.Ontology:
    """Load ontologies.

    TODO: update.
    """
    if use_cache:
        logger.debug("Using caching of turtle files")
        to_read = []
        logger.debug("Downloading missing ontologies...")
        for iri in iris:
            if "file://" in iri:
                logger.debug(f"{iri} is a local file.")
                to_read.append(iri)
                continue
            filename = _iri_to_filename(iri)
            to_read.append(filename)
            if filename.is_file():
                logger.info(f"Found {iri} in {filename}")
            else:
                inferred_url = _iri_to_inferred(iri)
                logger.info(f"Downloading {inferred_url} (inferred) to {filename}.")
                _download_ontology(inferred_url, filename)
    else:
        logger.debug("Not using caching of turtle files")
        to_read = iris

    # Read ontologies one by one
    world = ontopy.World()
    onto = world.get_ontology("ontology")
    for iri in to_read:
        logger.info(f"Reading {iri}")
        dep = world.get_ontology(iri).load()
        onto.imported_ontologies.append(dep)
    return onto


def _download_ontology(url: str, destination: os.PathLike) -> None:
    """TODO: docstring."""
    s = requests.Session()
    retries = urllib3.util.Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
    )
    s.mount("https://", requests.adapters.HTTPAdapter(max_retries=retries))
    res = s.get(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w") as f:
        f.write(res.text)


mammos_ontology = Ontology()
