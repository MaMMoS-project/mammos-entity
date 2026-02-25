from typing import Literal

import mammos_units as u
import pytest

import mammos_entity as me

LABEL = "ThermodynamicTemperature"
ALT_LABEL = "CurieTemperature"


# Intended use


def test_convert_entity_likes_converts_quantity_input():
    @me.convert_entity_likes
    def identity(
        temperature: me.typing.EntityLike[Literal[LABEL]],
    ):
        assert isinstance(temperature, me.Entity)
        assert temperature.ontology_label == LABEL
        return temperature

    result = identity(300 * u.K)
    assert isinstance(result, me.Entity)
    assert result.ontology_label == LABEL
    assert u.allclose(result.q, 300 * u.K)


def test_convert_entity_likes_uses_first_label_as_canonical():
    @me.convert_entity_likes
    def identity(
        temperature: me.typing.EntityLike[Literal[LABEL, ALT_LABEL]],
    ):
        return temperature

    result = identity(me.Entity(ALT_LABEL, 300 * u.K, description="input"))
    assert isinstance(result, me.Entity)
    assert result.ontology_label == LABEL
    assert result.description == "input"
    assert u.allclose(result.q, 300 * u.K)


def test_convert_entity_likes_passes_none_through_for_optional_annotation():
    @me.convert_entity_likes
    def identity(
        temperature: me.typing.EntityLike[Literal[LABEL]] | None,
    ):
        return temperature

    assert identity(None) is None


def test_convert_entity_likes_converts_optional_non_none_values():
    @me.convert_entity_likes
    def identity(
        temperature: me.typing.EntityLike[Literal[LABEL]] | None,
    ):
        return temperature

    result = identity(300)
    assert isinstance(result, me.Entity)
    assert result.ontology_label == LABEL
    assert u.allclose(result.q, 300 * u.K)


def test_convert_entity_likes_accepts_matching_return_entity():
    @me.convert_entity_likes
    def as_curie_temperature(
        temperature: me.typing.EntityLike[Literal[LABEL]],
    ) -> me.Entity[Literal[ALT_LABEL]]:
        return me.Entity(ALT_LABEL, temperature.q)

    result = as_curie_temperature(300)
    assert isinstance(result, me.Entity)
    assert result.ontology_label == ALT_LABEL
    assert u.allclose(result.q, 300 * u.K)


def test_convert_entity_likes_ignores_return_annotation_validation():
    @me.convert_entity_likes
    def as_curie_temperature(
        temperature: me.typing.EntityLike[Literal[LABEL]],
    ) -> me.Entity[Literal[ALT_LABEL]]:
        return temperature.q

    result = as_curie_temperature(300)
    assert u.allclose(result, 300 * u.K)


def test_convert_entity_likes_allows_dict_return_with_entity_annotation():
    @me.convert_entity_likes
    def as_dict(
        temperature: me.typing.EntityLike[Literal[LABEL]],
    ) -> dict[str, me.Entity[Literal[LABEL]]]:
        return {"temperature": temperature}

    result = as_dict(300)
    assert isinstance(result, dict)
    assert "temperature" in result
    assert isinstance(result["temperature"], me.Entity)
    assert result["temperature"].ontology_label == LABEL


def test_convert_entity_likes_supports_var_positional_annotation():
    @me.convert_entity_likes
    def identity(*temperature: me.typing.EntityLike[Literal[LABEL, ALT_LABEL]]):
        return temperature

    result = identity(300, 301 * u.K, me.Entity(ALT_LABEL, 302 * u.K))
    assert isinstance(result, tuple)
    assert all(isinstance(item, me.Entity) for item in result)
    assert all(item.ontology_label == LABEL for item in result)
    assert u.allclose(
        u.Quantity([item.value for item in result], u.K),
        [300, 301, 302] * u.K,
    )


def test_convert_entity_likes_supports_var_keyword_annotation():
    @me.convert_entity_likes
    def identity(**temperature: me.typing.EntityLike[Literal[LABEL, ALT_LABEL]]):
        return temperature

    result = identity(a=300, b=301 * u.K, c=me.Entity(ALT_LABEL, 302 * u.K))
    assert isinstance(result, dict)
    assert set(result) == {"a", "b", "c"}
    assert all(isinstance(item, me.Entity) for item in result.values())
    assert all(item.ontology_label == LABEL for item in result.values())
    assert u.allclose(
        u.Quantity([result[key].value for key in ("a", "b", "c")], u.K),
        [300, 301, 302] * u.K,
    )


# Misuse and unsupported contracts


def test_convert_entity_likes_rejects_incompatible_entity_label():
    @me.convert_entity_likes
    def identity(
        temperature: me.typing.EntityLike[Literal[LABEL]],
    ):
        return temperature

    with pytest.raises(TypeError, match="expects one of"):
        identity(me.Entity("ExternalMagneticField", 1))


def test_convert_entity_likes_rejects_list_annotation():
    with pytest.raises(TypeError, match="concat_flat"):

        @me.convert_entity_likes
        def identity(
            temperature: list[me.typing.EntityLike[Literal[LABEL]]],
        ):
            return temperature


def test_convert_entity_likes_rejects_tuple_annotation():
    with pytest.raises(TypeError, match="concat_flat"):

        @me.convert_entity_likes
        def identity(
            temperature: tuple[
                me.typing.EntityLike[Literal[LABEL]],
                ...,
            ],
        ):
            return temperature


def test_convert_entity_likes_rejects_dict_annotation():
    with pytest.raises(TypeError, match="unsupported"):

        @me.convert_entity_likes
        def identity(
            temperature: dict[str, me.typing.EntityLike[Literal[LABEL]]],
        ):
            return temperature


def test_convert_entity_likes_rejects_mixed_union_annotation():
    with pytest.raises(TypeError, match="unsupported"):

        @me.convert_entity_likes
        def identity(
            temperature: me.typing.EntityLike[Literal[LABEL]] | dict[str, float],
        ):
            return temperature


def test_convert_entity_likes_requires_literal_labels_for_parameter():
    with pytest.raises(TypeError, match="Literal"):

        @me.convert_entity_likes
        def identity(
            temperature: me.typing.EntityLike[str],
        ):
            return temperature
