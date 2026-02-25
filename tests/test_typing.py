from typing import Literal, get_args, get_origin

import mammos_entity as me


def test_ontology_label_typevar_exported_in_typing_module():
    assert hasattr(me.typing, "OntologyLabelT")


def test_entity_annotation_is_generic():
    annotation = me.Entity[Literal["CurieTemperature"]]
    assert get_origin(annotation) is me.Entity
    assert get_args(get_args(annotation)[0]) == ("CurieTemperature",)


def test_entity_like_annotation_is_generic():
    annotation = me.typing.EntityLike[
        Literal["ThermodynamicTemperature", "CurieTemperature"]
    ]
    entity_annotation = next(
        argument
        for argument in get_args(annotation)
        if get_origin(argument) is me.Entity
    )
    assert get_args(get_args(entity_annotation)[0]) == (
        "ThermodynamicTemperature",
        "CurieTemperature",
    )
