"""Loads and provides access to MaMMoS ontology which is part of EMMO.

Loads and provides access to the MaMMoS magnetic materials ontology, including
everything from the EMMO ontology, via the `EMMOntoPy` library. The ontology is loaded
from ``.ttl`` (Turtle) files distributed with mammos-entity.
"""

from __future__ import annotations

from collections.abc import Iterable
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING

import ontopy

from mammos_entity._entity import Entity

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
        self._iris = iris
        if initialize:
            self.initialize()
        else:
            self._initialized = False

    def __str__(self):
        """TODO: docstring."""
        out = "Ontology:\n"
        if self._iris is None:
            out += "- local `magmo`."
        else:
            out += "\n".join(f"- {iri}" for iri in self._iris)
        return out

    def __repr__(self):
        """TODO: docstring."""
        return f"Ontology({self._iris!r})"

    def initialize(self, verbose: bool = False):
        """TODO: docstring."""
        if self._iris is None:
            self._ontopy_ontology = load_offline_ontologies(verbose=verbose)
        else:
            self._ontopy_ontology = load_online_ontologies(self._iris, verbose=verbose)
        self._initialized = True

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
        ontology_label: str,
        value: mammos_entity.Entity | mammos_units.Quantity | numpy.typing.ArrayLike = 0,
        unit: str | None | mammos_units.UnitBase = None,
        *,
        description: str = "",
    ):
        """TODO: docstring."""
        if not self._initialized:
            self.initialize()
            self._initialized = True
        return Entity(ontology_label, value, unit, description=description, ontology=self)


def load_offline_ontologies(verbose: bool = False) -> ontopy.ontology.Ontology:
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
    world.get_ontology(emmo_ttl).load()
    # now load MaMMoS ontology, which builds upon EMMO; with EMMO already loaded
    # no internet access is required to resolve 'owl:imports <https://w3id.org/emmo'
    mammos_ttl = f"file://{ontology_dir / 'magnetic-materials.ttl'!s}"
    logger.debug("loading mammos ttl from '%s'", mammos_ttl)
    mammos_ontology = world.get_ontology(mammos_ttl).load()
    return mammos_ontology


def load_online_ontologies(iris: Iterable[str], verbose: bool = False) -> ontopy.ontology.Ontology:
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
