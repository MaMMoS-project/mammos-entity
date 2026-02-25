"""Decorators for annotation-driven entity conversion."""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable
from functools import wraps
from typing import (
    Any,
    Literal,
    ParamSpec,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

import astropy.units

from mammos_entity._entity import Entity
from mammos_entity._ontology import mammos_ontology

P = ParamSpec("P")
R = TypeVar("R")
_ParameterContract = tuple[tuple[str, ...], bool]


def convert_entity_likes(func: Callable[P, R]) -> Callable[P, R]:
    """Convert entity-like parameters to entities.

    Supported parameter annotations:

    - ``EntityLike[Literal["Label"]]``
    - ``EntityLike[Literal["Label1", "Label2", ...]]``
    - Optional form of the above, e.g. ``EntityLike[Literal["Label"]] | None``
    - The same scalar contracts for ``*args`` and ``**kwargs`` values

    If multiple labels are listed in ``Literal[...]``, the first label is canonical for
    input conversion.

    Notes:
    - Return annotations and return values are ignored by this decorator.
    - Container annotations such as ``list[EntityLike[...]]`` and
      ``tuple[EntityLike[...], ...]`` are intentionally unsupported. For these use
      :py:func:`mammos_entity.operations.concat_flat` explicitly.

    Args:
        func: Callable to decorate.

    Returns:
        Wrapped callable with converted inputs.

    Examples:
        Basic conversion:

        >>> from typing import Literal
        >>> import mammos_entity as me
        >>> import mammos_units as u
        >>> @me.convert_entity_likes
        ... def f(t: me.typing.EntityLike[Literal["ThermodynamicTemperature"]]):
        ...     return t
        >>> isinstance(f(300 * u.K), me.Entity)
        True

        Optional passthrough:

        >>> @me.convert_entity_likes
        ... def f_opt(
        ...     t: me.typing.EntityLike[Literal["ThermodynamicTemperature"]] | None,
        ... ):
        ...     return t
        >>> f_opt(None) is None
        True

        Var-positional conversion:

        >>> @me.convert_entity_likes
        ... def f_args(
        ...     *t: me.typing.EntityLike[
        ...         Literal["ThermodynamicTemperature", "CurieTemperature"]
        ...     ],
        ... ):
        ...     return t
        >>> all(
        ...     x.ontology_label == "ThermodynamicTemperature"
        ...     for x in f_args(300, me.Entity("CurieTemperature", 301))
        ... )
        True

    """
    signature = inspect.signature(func)
    annotations = get_type_hints(func, include_extras=True)
    converters: dict[str, _ParameterContract] = {}

    for name, annotation in annotations.items():
        if name == "return":
            continue
        contract = _parse_parameter_contract(annotation)
        if contract is None:
            continue
        _check_labels_exist(contract[0])
        converters[name] = contract

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()

        for parameter_name, contract in converters.items():
            if parameter_name not in bound_arguments.arguments:
                continue

            parameter = signature.parameters[parameter_name]
            parameter_value = bound_arguments.arguments[parameter_name]

            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                bound_arguments.arguments[parameter_name] = tuple(
                    _convert_parameter_value(
                        item, contract, f"{parameter_name}[{index}]"
                    )
                    for index, item in enumerate(parameter_value)
                )
            elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
                bound_arguments.arguments[parameter_name] = {
                    key: _convert_parameter_value(
                        value, contract, f"{parameter_name}.{key}"
                    )
                    for key, value in parameter_value.items()
                }
            else:
                bound_arguments.arguments[parameter_name] = _convert_parameter_value(
                    parameter_value, contract, parameter_name
                )

        return func(*bound_arguments.args, **bound_arguments.kwargs)

    return wrapper


def _parse_parameter_contract(annotation: Any) -> _ParameterContract | None:
    """Parse one parameter annotation into a scalar conversion contract."""
    # Normalize optional annotations once so downstream parsing only handles the
    # non-None part of the contract.
    inner_annotation, allow_none = _split_optional(annotation)
    origin = get_origin(inner_annotation)

    if origin in (list, tuple):
        if _contains_entity_like_annotation(inner_annotation):
            raise TypeError(
                "Container annotations are unsupported in convert_entity_likes. "
                "Use operations.concat_flat for list/tuple entity-like data."
            )
        return None

    if origin is dict:
        if _contains_entity_like_annotation(inner_annotation):
            raise TypeError(
                "unsupported annotation for convert_entity_likes parameter."
            )
        return None

    if origin in (Union, types.UnionType):
        # EntityLike[...] is represented at runtime as a union of concrete types.
        # We therefore infer an EntityLike-style contract by finding one Entity[...]
        # branch (labels) plus a Quantity branch.
        labels: tuple[str, ...] | None = None
        non_entity_args: list[Any] = []
        for argument in get_args(inner_annotation):
            argument_labels = _labels_from_entity_annotation(argument)
            if argument_labels is not None:
                if labels is None:
                    labels = argument_labels
                else:
                    # Top-level union-of-Entity annotations is documentation only.
                    return None
                continue

            argument_origin = get_origin(argument)
            if argument_origin in (list, tuple):
                raise TypeError(
                    "Container annotations are unsupported in convert_entity_likes. "
                    "Use operations.concat_flat for list/tuple entity-like data."
                )
            if argument_origin is dict:
                raise TypeError(
                    "unsupported annotation for convert_entity_likes parameter."
                )
            non_entity_args.append(argument)

        if labels is not None:
            # Convert only EntityLike-style unions.
            if astropy.units.Quantity not in non_entity_args:
                return None
            return labels, allow_none

        if _contains_entity_like_annotation(inner_annotation):
            raise TypeError(
                "unsupported annotation for convert_entity_likes parameter."
            )
        return None

    labels = _labels_from_entity_like_annotation(inner_annotation)
    if labels is not None:
        return labels, allow_none

    return None


def _split_optional(annotation: Any) -> tuple[Any, bool]:
    """Split ``T | None`` into ``(T, True)``.

    If ``None`` appears in a larger union, it is removed and the remaining union is
    returned with ``True``.
    """
    origin = get_origin(annotation)
    if origin not in (Union, types.UnionType):
        return annotation, False

    args = get_args(annotation)
    non_none_args = [argument for argument in args if argument is not type(None)]  # noqa: E721
    has_none = len(non_none_args) != len(args)

    if not has_none:
        return annotation, False
    if not non_none_args:
        return annotation, True
    if len(non_none_args) == 1:
        return non_none_args[0], True

    # Rebuild the union with ``|`` so later logic can continue using ``get_origin``
    # / ``get_args`` consistently on a non-optional annotation.
    merged_annotation = non_none_args[0]
    for argument in non_none_args[1:]:
        merged_annotation = merged_annotation | argument
    return merged_annotation, True


def _labels_from_entity_like_annotation(annotation: Any) -> tuple[str, ...] | None:
    """Extract ontology labels from scalar entity-like annotations."""
    # EntityLike aliases resolve to unions containing exactly one Entity[Literal[...]]
    # branch plus a Quantity branch.
    if get_origin(annotation) not in (Union, types.UnionType):
        return None

    labels: tuple[str, ...] | None = None
    has_quantity = False
    for argument in get_args(annotation):
        argument_labels = _labels_from_entity_annotation(argument)
        if argument_labels is not None:
            if labels is None:
                labels = argument_labels
            continue
        if argument is astropy.units.Quantity:
            has_quantity = True

    if labels is not None and has_quantity:
        return labels
    return None


def _contains_entity_like_annotation(annotation: Any) -> bool:
    """Return ``True`` if an annotation tree contains entity-like contracts."""
    if _labels_from_entity_like_annotation(annotation) is not None:
        return True

    origin = get_origin(annotation)
    if origin in (list, tuple, dict, Union, types.UnionType):
        for argument in get_args(annotation):
            if argument is Ellipsis:
                continue
            if _contains_entity_like_annotation(argument):
                return True
    return False


def _labels_from_entity_annotation(annotation: Any) -> tuple[str, ...] | None:
    """Extract ontology labels from ``Entity[Literal[...]]`` annotations."""
    if get_origin(annotation) is not Entity:
        return None

    annotation_args = get_args(annotation)
    if len(annotation_args) != 1:
        raise TypeError("Entity[...] annotation requires exactly one type argument.")

    literal_argument = annotation_args[0]
    if get_origin(literal_argument) is not Literal:
        raise TypeError("Entity[...] annotations must use Literal[...] labels.")

    labels = get_args(literal_argument)
    if not labels:
        raise TypeError("Literal[...] for Entity annotations must not be empty.")
    if not all(isinstance(label, str) for label in labels):
        raise TypeError("Entity labels must be string literals.")
    return labels


def _check_labels_exist(labels: tuple[str, ...]) -> None:
    """Validate that all labels exist in the ontology."""
    for label in labels:
        mammos_ontology.get_by_label(label)


def _convert_parameter_value(
    value: Any, contract: _ParameterContract, parameter_name: str
) -> Entity | None:
    """Convert one scalar parameter value according to one parsed contract."""
    labels, allow_none = contract

    if value is None and allow_none:
        return None

    canonical_label = labels[0]
    if isinstance(value, Entity):
        if value.ontology_label not in labels:
            raise TypeError(
                f"Argument '{parameter_name}' expects one of {labels}, "
                f"got '{value.ontology_label}'."
            )
        if value.ontology_label == canonical_label:
            return value
        return Entity(canonical_label, value.quantity, description=value.description)

    return Entity(canonical_label, value)
