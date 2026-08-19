"""Test command line tools."""

import os
import shlex
import shutil
import subprocess

import pytest

import mammos_entity as me


def test_mammos_entity_executable():
    """Test that the `download-ontology` executable exist."""
    exe = shutil.which("mammos-entity")
    assert exe is not None


@pytest.mark.xfail
def test_mammos_entity_ontology_download_empty_iri():
    """Test that `mammos-entity ontology download` fails if no IRIs are given."""
    command = shlex.split("mammos-entity ontology download")
    res = subprocess.run(command)
    res.check_returncode()


@pytest.mark.parametrize(
    ("iri", "domain", "version"),
    (
        ("https://w3id.org/emmo/1.0.3/", "emmo", "1.0.3"),
        ("https://w3id.org/emmo/domain/magnetic-materials/0.0.5", "magnetic-materials", "0.0.5"),
    ),
)
def test_mammos_entity_ontology_download_single_iri(iri, domain, version):
    """Test downloading single IRI.

    First we clean up the cache directory. Then we check that the downloads are in the right directory.
    """
    command = shlex.split("mammos-entity ontology clear-cache")
    res = subprocess.run(command)
    res.check_returncode()
    command = shlex.split(f"mammos-entity ontology download {iri}")
    res = subprocess.run(command)
    res.check_returncode()
    assert (me._CACHE_DIR / domain / version / "inferred.ttl").is_file()


def test_mammos_entity_ontology_download_multiple_iri():
    """Test downloading multiple IRI.

    First we clean up the cache directory. Then we check that the downloads are in the right directory.
    """
    command = shlex.split("mammos-entity ontology clear-cache")
    res = subprocess.run(command)
    res.check_returncode()
    emmo_iri = "https://w3id.org/emmo/1.0.3"
    magmo_iri = "https://w3id.org/emmo/domain/magnetic-materials/0.0.5"
    command = shlex.split(f"mammos-entity ontology download {emmo_iri} {magmo_iri}")
    res = subprocess.run(command)
    res.check_returncode()
    assert (me._CACHE_DIR / "emmo" / "1.0.3" / "inferred.ttl").is_file()
    assert (me._CACHE_DIR / "magnetic-materials" / "0.0.5" / "inferred.ttl").is_file()


def test_mammos_entity_ontology_clear_cache():
    """Test command that clears cache directory.

    We run the command before and after we download an ontology.
    """
    command = shlex.split("mammos-entity ontology clear-cache")
    res = subprocess.run(command)
    res.check_returncode()
    assert not os.listdir(me._CACHE_DIR)
    command = shlex.split("mammos-entity ontology download https://w3id.org/emmo/1.0.3")
    res = subprocess.run(command)
    res.check_returncode()
    command = shlex.split("mammos-entity ontology clear-cache")
    res = subprocess.run(command)
    res.check_returncode()
    assert not os.listdir(me._CACHE_DIR)
