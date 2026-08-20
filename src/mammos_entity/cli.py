"""Command line tools for mammos entity.

The following commands are provided:
- `mammos-entity ontology download [iris]`: download ontology specified by IRIs.
- `mammos-entity ontology clear-cache`: clear ontology caching directory.
"""

import argparse
import logging

import mammos_entity as me

logger = logging.getLogger(__package__)


def main() -> None:
    """mammos-entity command line interface entrypoint."""
    parser = argparse.ArgumentParser(
        prog="mammos-entity",
        description="mammos-entity command line tools.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show detailed information")

    # sub-commands of `mammos-entity`
    main_subparser = parser.add_subparsers(dest="subcommand", required=True)
    ontology_parser = main_subparser.add_parser(
        "ontology",
        description=(
            "Ontology tools. "
            "The sub-command `download` downloads ontologies to cache, inside the caching directory `mammos_entity`. "
            "To specify an ontology, its `versionIRI` must be given. For example, `https://w3id.org/emmo/1.0.3` for "
            "EMMO, or `https://w3id.org/emmo/domain/magnetic-materials/0.0.5` for any domain ontology."
        ),
    )

    # sub-commands of `mammos-entity ontology`
    ontology_subparser = ontology_parser.add_subparsers(dest="ontology_command", required=True)
    download_parser = ontology_subparser.add_parser("download", help="Download ontology to caching directory.")
    download_parser.add_argument("iris", help="one or more ontology IRIs", nargs="+")
    ontology_subparser.add_parser("clear-cache", help="Clear cache directory.")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)

    if args.subcommand == "ontology":
        match args.ontology_command:
            case "download":
                download(args.iris)
            case "clear-cache":
                clear_cache()


def download(iris: list[str]) -> None:
    """Download ontology specified by versionIRI.

    Args:
        iris: List of ontology versionIRIs.
    """
    for iri in iris:
        inferred = me._ontology._iri_to_inferred(iri)
        filename = me._ontology._iri_to_filename(iri)
        if filename.exists():
            logger.info(f"Ontology file {filename} already exists. Overwriting.")
        else:
            logger.info(f"Downloading: {filename}.")
        me._ontology._download_ontology(inferred, filename)


def clear_cache() -> None:
    """Command-line entry point to clear the cache from downloaded ontologies."""
    if me._CACHE_DIR.is_dir():
        for domain in me._CACHE_DIR.iterdir():
            for version in domain.iterdir():
                for ttl in version.iterdir():
                    ttl.unlink()
                    logger.debug(f"Removed turtle file: {ttl}")
                version.rmdir()
                logger.debug(f"Removed directory: {version}")
            domain.rmdir()
            logger.debug(f"Removed directory: {domain}")
