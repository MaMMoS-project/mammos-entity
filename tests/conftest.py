import pytest

import mammos_entity as me


@pytest.fixture(scope="session")
def onto_class_list():
    return [str(cls.prefLabel[0]) for cls in me.mammos_ontology.classes()]
