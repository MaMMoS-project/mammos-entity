"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology, including
everything from the EMMO ontology, via the `EMMOntoPy` library. The ontology is loaded
from ``.ttl`` (Turtle) files distributed with mammos-entity.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

import ontopy

from mammos_entity._entity import Entity
from mammos_entity._entity_collection import EntityCollection

logger = getLogger(__name__)


if TYPE_CHECKING:
    import mammos_units
    import numpy.typing
    import ontopy.ontology

    import mammos_entity


class Ontology:
    """TODO: docstring."""

    def __init__(self, iris: Iterable[str] | None = None, initialize: bool = False):
        """TODO: docstring."""
        self._iris = sorted(iris, reverse=True) if iris else iris
        self._initialized = False
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

    def initialize(self, verbose: bool = False):
        """TODO: docstring."""
        if self._initialized:
            warnings.warn(
                "Already initialized. Re-initializing.",
                stacklevel=1,
            )
        if self._iris is None:
            self._ontopy_ontology, self._iris = _load_local_ontologies(verbose=verbose)
            self._local = True
        else:
            self._ontopy_ontology = _load_online_ontologies(self._iris, verbose=verbose)
            self._local = False
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
            self.iris.sort(reverse=True)

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


def _load_local_ontologies(verbose: bool = False) -> (ontopy.ontology.Ontology, list[str]):
    """Load EMMO and MaMMoS ontology from 'ontology' directory.

    The returned ontology object contains all definitions from both ontologies, EMMO is
    in the attribute ``.imported_ontologies`` and accessible in other methods when using
    ``imported=True``.

    """
    if verbose:
        print("Reading local MagMO")
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


mammos_ontology = Ontology()
