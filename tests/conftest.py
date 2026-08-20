"""Test Configuration."""

import pytest

import mammos_entity as me


@pytest.fixture(scope="session")
def magmo():
    magmo = me.mammos_ontology
    magmo.initialize()
    return magmo
