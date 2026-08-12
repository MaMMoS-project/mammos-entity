"""Command line tools for mammos entity.

TODO: write list of commands
"""

import argparse

import mammos_entity as me


def download_ontology():
    """Command-line entry point to download ontologies."""
    parser = argparse.ArgumentParser(
        prog="download-ontologies",
        description="Download ontology defined by a certain IRI.",
    )
    parser.add_argument(
        "ontologies",
        type=str,
        nargs="*",
        required=True,
        help=("IRI(s) of ontologies to be downloaded."),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )

    args = parser.parse_args()
    for iri in args.iris:
        inferred = me._ontology._iri_to_inferred(iri)
        filename = me._ontology._iri_to_filename(iri)
        if args.verbose:
            if filename.exists():
                print(f"Ontology file {filename} already exists. Overwriting.")
            else:
                print(f"Downloading: {filename}.")
        me._download_ontology(inferred, filename)


def clear_cache():
    """Command-line entry point to clear the cache from downloaded ontologies."""
    if me._CACHE_DIR.is_dir():
        for domain in me._CACHE_DIR.iterdir():
            domain.unlink()
