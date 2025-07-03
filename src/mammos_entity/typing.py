"""Custom types for mammos-entity."""

from __future__ import annotations

import inspect
import typing
from functools import wraps
from typing import Annotated, Generic, TypeVar

from mammos_units import Quantity
from numpy.typing import ArrayLike

import mammos_entity as me

_LabelT = TypeVar("_LabelT", bound=str)


class _EntityLike(Generic[_LabelT]):
    """
    Allows   EntityLike["my_label"]   in type annotations.

    At static-checking time   EntityLike[...]
        ==  Entity | numpy.typing.ArrayLike

    At run time the annotation is stored as
        Annotated[Entity | Quantity | ArrayLike, ("EntityLikeLabel", <label>)]
    so the label can later be retrieved via reflection.
    """

    __slots__ = ()

    def __class_getitem__(cls, label: str):
        if not isinstance(label, str):
            raise TypeError("EntityLike[...] needs a literal str label")
        return Annotated[
            me.Entity | Quantity | ArrayLike,  # what type checkers see
            ("EntityLabel", label),  # run-time metadata
        ]


# public alias
EntityLike = _EntityLike  # type: ignore[assignment]


def _extract_entitylike_label(annotation) -> str | None:
    """Extract label of an EntityLike["label"] annotation.

    Return the label of an  EntityLike["label"]  annotation,
    or  None  if the annotation is something else.
    """
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        _, *meta = typing.get_args(annotation)
        for item in meta:
            if isinstance(item, tuple) and item[:1] == ("EntityLabel",):
                return typing.cast(str, item[1])
    return None


def runtime_convert_entitylikes(func):
    """Decorator to conver EntityLike to Entity arguments."""  # noqa: D401
    sig = inspect.signature(func)
    # include_extras=True keeps the Annotated metadata we need
    hints = typing.get_type_hints(func, include_extras=True)
    param_names = list(sig.parameters)  # positional index → parameter name

    @wraps(func)
    def wrapper(*args, **kwargs):
        # --- positional arguments -----------------------------------
        args = list(args)  # mutable copy
        for idx, value in enumerate(args):
            name = param_names[idx]
            label = _extract_entitylike_label(hints.get(name))
            if label is not None:
                args[idx] = me.Entity(label, value)

        # --- keyword arguments --------------------------------------
        new_kwargs = {}
        for name, value in kwargs.items():
            label = _extract_entitylike_label(hints.get(name))
            if label is not None:
                new_kwargs[name] = me.Entity(label, value)
            else:
                new_kwargs[name] = value

        # call the wrapped function
        return func(*args, **new_kwargs)

    return wrapper
