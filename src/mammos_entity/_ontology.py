"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology, including everything from the EMMO ontology,
via the `EMMOntoPy` library. The ontology is loaded from ``.ttl`` (Turtle) files distributed with mammos-entity.

To uniquely identify ontologies, a ``versionIRI`` is used. This consist of the ontology name and the version string.
This is, e.g.
- ``https://w3id.org/1.0.3/emmo/`` for EMMO 1.0.3
- ``https://w3id.org/emmo/domain/magnetic-materials/0.0.5/`` for MagMO 0.0.5
- ``https://w3id.org/emmo/domain/electrochemistry/0.37.2/`` for ECHO 0.37.2

Observe that a different range of versionIRIs are accepted, for example the inferred versionIRI
``https://w3id.org/emmo/domain/magnetic-materials/0.0.5/inferred`` is also valid.
"""

from __future__ import annotations

import os
import re
import shutil
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

logger = getLogger(__package__)

if TYPE_CHECKING:
    import mammos_units
    import numpy.typing
    import ontopy.ontology

    import mammos_entity


class Ontology:
    """An object storing different ontologies information.

    Entities can be created using :py:method:`Entity`. It is recommended to define entities via their IRIs. If the same
    entity appears in different ontologies, the object is created from the the first available one.

    When initialized, each ontology is automatically downloaded and cached for future use.

    .. version-added: 0.14.0
       The Ontology class.
    """

    def __init__(self, iris: Iterable[str] | None = None, initialize: bool = False) -> None:
        """Initialize an ontology object.

        Args:
            iris: List of ``versionIRI`` of all the ontologies to be loaded.
            initialize: Whether to load the ontology at this stage. It is still possible to add other ontologies later
                with the method :py:method:`add_iri`.
        """
        if iris is None:
            self._iris = ["https://w3id.org/emmo/domain/magnetic-materials/0.0.5/inferred"]
        else:
            self._iris = list(iris)
        self._initialized = False
        self._ontopy_ontology = None
        if initialize:
            self.initialize()

    def __str__(self) -> str:
        _init = " (initialized)" if self._initialized else ""
        out = f"Ontology:{_init}\n"
        if self._iris is None:
            out += "- local `magmo`."
        else:
            out += "\n".join(f"- {iri}" for iri in self._iris)
        return out

    def __repr__(self) -> str:
        arg = f"{self._iris!r}" if self._iris else ""
        return f"Ontology({arg})"

    @property
    def iris(self) -> list[str]:
        """List of ``versionIRI`` urls of all loaded ontology."""
        return self._iris

    @iris.setter
    def iris(self, _) -> None:
        """Assign iris directly.

        Trying to assign the iris directly will fail. Use the method :py:method:``add_iri`` instead.

        Raises:
            RuntimeError: The method :py:method:``add_iri`` should be used instead of this property.
        """
        raise RuntimeError(
            "Do not assign the iris directly. To add new iris, use the method "
            "`add_iri`. To remove iris, please initiate a new `Ontology` object."
        )

    def initialize(self, use_cache: bool = True) -> None:
        """Initialize ontologies.

        Download the ontologies and load them into an :py:class:`ontopy.ontology.Ontology` object.
        If caching is activated, the download step is skipped.

        Args:
            use_cache: Whether to use caching of ontologies.
        """
        logger.debug(f"Initializing with iris={self.iris!r}")
        if self._initialized:
            warnings.warn(
                "Already initialized. Re-initializing.",
                stacklevel=1,
            )
        self._ontopy_ontology = _load_ontologies(self.iris, use_cache=use_cache)
        self._initialized = True

    def add_iri(self, iri: str) -> None:
        """Add ontology from a ``versionIRI`` string.

        Args:
            iri: IRI of the ontology expressed as ``versionIRI``.
        """
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
        """Search entity labels by name in the current ontology.

        The string ``text`` is searched into ``label``, ``prefLabel``, and ``altLabel`` of all entities.
        The match is case sensitive. The returned label is always the ``prefLabel``.

        This function uses internally the method ``.search()`` of :py:class:`ontopy.ontology.Ontology`.

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
            >>> onto = me.Ontology(initialize=True)
            >>> onto.search_labels("ShapeAnisotropy")
            ['ShapeAnisotropy', 'ShapeAnisotropyConstant']

            >>> onto.search_labels("Magnetization")
            ['MagneticMomentPerUnitMass', 'Magnetization', 'MassMagnetizationUnit', 'Remanence', 'SaturationMagnetization', 'SpontaneousMagnetization']

            ``'MagneticMomentPerUnitMass'`` appears because ``'MassMagnetization'`` is
            in its ``altLabel``.

            >>> onto.search_labels("Magnetization", auto_wildcard=False)
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
    ) -> mammos_entity.Entity:
        """Create Entity from this ontology.

        Args:
            ontology_label: Label of the entity in any of the loaded ontologies.
            value: Numerical value of the entity.
            unit: Physical unit of the entity.
            iri: IRI of the entity in any of the loaded ontologies.
            description: Optional description string.

        Returns:
           Entity representing the ontology concept.
        """
        if not self._initialized:
            self.initialize()
        return Entity(ontology_label, value, unit, iri=iri, description=description, ontology=self)


def _iri_to_filename(iri: str) -> os.PathLike:
    """Get path of cached ontology on the local system.

    Args:
        iri: IRI of the ontology expressed as ``versionIRI``.

    Returns:
        Path of the cached ontology.
    """
    name, version = _iri_to_info(iri)
    return me._CACHE_DIR / name / version / "inferred.ttl"


def _iri_to_inferred(iri: str) -> str:
    """Get url of inferred ontology from IRI.

    Args:
        iri: IRI of the ontology expressed as ``versionIRI``.

    Returns:
        URL of inferred ontology.
    """
    emmo_domain = "https://w3id.org/emmo"
    name, version = _iri_to_info(iri)
    if name == "emmo":
        return f"{emmo_domain}/{version}/inferred"
    else:
        return f"{emmo_domain}/domain/{name}/{version}/inferred"


def _iri_to_info(iri: str) -> tuple(str):
    """Get ontology essential information from IRI.

    Args:
        iri: IRI of the ontology expressed as ``versionIRI``.

    Returns:
        tuple ``(ontology_name, version_number)``. The ``ontology_name`` is ``emmo`` if the IRI points to EMMO,
        while it is the domain name if it points to any EMMO-based domain ontology.

    Raises:
        ValueError: The IRI does not correspond to an EMMO IRI, i.e. it does not start with `https://w3id.org/emmo`.
    """
    if iri == "https://w3id.org/1.0.3/emmo":
        # HACK: EMMO 1.0.3 inferred IRI is broken
        return ("emmo", "1.0.3")
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


def _load_ontologies(iris: Iterable[str], use_cache: bool = True) -> ontopy.ontology.Ontology:
    """Load ontologies.

    If the IRI points to a local file, the cache parameter is ignored. Otherwise, the ontology is downloaded and
    cached so that future loadings are faster.

    Args:
        iris: List of ``versionIRI`` strings of all ontologies to load.
        use_cache: Whether to use cached ontologies.

    Returns:
        Loaded ontology.
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
            to_read.append(f"file://{filename}")
            if filename.is_file():
                logger.info(f"Found {iri} in {filename}")
            else:
                inferred_url = _iri_to_inferred(iri)
                if inferred_url == "https://w3id.org/emmo/domain/magnetic-materials/0.0.5/inferred":
                    _copy_packaged_ontology(filename)
                else:
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
        if dep.metadata.has("http://purl.org/vocab/vann/preferredNamespacePrefix"):
            prefix = dep.metadata.preferredNamespacePrefix[0]
            logger.debug(f"Changing prefix of {dep} to {prefix}.")
            dep.name = prefix  # change repr of entities in this ontology
            dep.prefix = prefix  # change prefix - used in some operations
        else:
            logger.debug(f"Ontology {dep} does not have a `preferredNamespacePrefix`.")
        onto.imported_ontologies.append(dep)
    return onto


def _copy_packaged_ontology(destination: os.PathLike) -> None:
    """Copy packaged ontology to cache directory.

    destination: path of the cached ontology.
    """
    logger.info("Using local MagMO packaged with mammos-entity.")
    magmo = Path(__file__).parent / "ontology" / "magmo-inferred.ttl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(magmo, destination)
    logger.debug(f"Copied {magmo} to {destination}.")


def _download_ontology(url: str, destination: os.PathLike) -> None:
    """Download ontology.

    Args:
        url: URL to download.
        destination: Path where to store the cached ontology.
    """
    logger.info(f"Downloading {url} (inferred) to {destination}.")
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


def search_labels(text: str, auto_wildcard: bool = True) -> list[str]:
    """Search entity labels by name in MagMO.

    The string ``text`` is searched into ``label``, ``prefLabel``, and ``altLabel`` of all entities of the magnetic
    materials domain ontology (MagMO). The match is case sensitive. The returned label is always the ``prefLabel``.

    If the object `mammos_entity.mammos_ontology` is not initialized, this function will initialize it.

    Args:
        text: String to match.
        auto_wildcard: If True, the wildcard ``*`` is added at the beginning and at the end of the string ``text``.
            This allows partial matches, finding labels containing ``text``. If False, only labels identical to
            ``text`` are returned.

            Passing ``"text", auto_wildcard=True`` is identical to passing ``"*text*", auto_wildcard=False``.

    Examples:
        >>> import mammos_entity as me
        >>> me.search_labels("ShapeAnisotropy")
        ['ShapeAnisotropy', 'ShapeAnisotropyConstant']

        >>> me.search_labels("Magnetization")
        ['MagneticMomentPerUnitMass', 'Magnetization', 'MassMagnetizationUnit', 'Remanence', 'SaturationMagnetization', 'SpontaneousMagnetization']

        ``'MagneticMomentPerUnitMass'`` appears because ``'MassMagnetization'`` is in its ``altLabel``.

        >>> me.search_labels("Magnetization", auto_wildcard=False)
        ['Magnetization']

    """  # noqa:E501
    if not mammos_ontology._initialized:
        mammos_ontology.initialize()
    return mammos_ontology.search_labels(text, auto_wildcard=auto_wildcard)
