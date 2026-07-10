"""Helpers for notebook HTML representations."""

from __future__ import annotations

import importlib.resources
from functools import cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing


_ENTITY_REPR_SUMMARY_EDGE_ITEMS = 3
_ENTITY_REPR_EXPANDED_THRESHOLD = 100
_ENTITY_REPR_MAX_INLINE_CHARS = 80


def _strip_array_repr_brackets(text: str) -> str:
    """Remove the outer brackets from a one-dimensional NumPy repr string."""
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1]
    return text


def _format_array_repr_summary(value: numpy.typing.ArrayLike) -> str:
    """Format a flattened preview for array values in HTML reprs."""

    def compact(text: str) -> str:
        return " ".join(text.split())

    flattened = np.ravel(value)
    if flattened.size <= 2 * _ENTITY_REPR_SUMMARY_EDGE_ITEMS:
        return compact(
            _strip_array_repr_brackets(
                np.array2string(flattened, max_line_width=10_000)
            )
        )
    head = compact(
        _strip_array_repr_brackets(
            np.array2string(
                flattened[:_ENTITY_REPR_SUMMARY_EDGE_ITEMS],
                max_line_width=10_000,
            )
        )
    )
    tail = compact(
        _strip_array_repr_brackets(
            np.array2string(
                flattened[-_ENTITY_REPR_SUMMARY_EDGE_ITEMS:],
                max_line_width=10_000,
            )
        )
    )
    return f"{head} ... {tail}"


def _array_repr_expanded_edgeitems(value: numpy.typing.ArrayLike) -> int:
    """Choose NumPy edgeitems for a bounded expanded array repr."""
    array = np.asarray(value)
    if array.ndim <= 1:
        return _ENTITY_REPR_EXPANDED_THRESHOLD // 2
    return max(1, int((_ENTITY_REPR_EXPANDED_THRESHOLD ** (1 / array.ndim)) / 2))


def _format_array_repr_expanded(value: numpy.typing.ArrayLike) -> str:
    """Format a bounded expanded representation for array values in HTML reprs."""
    array = np.asarray(value)
    with np.printoptions(
        threshold=_ENTITY_REPR_EXPANDED_THRESHOLD,
        edgeitems=_array_repr_expanded_edgeitems(array),
    ):
        return repr(array)


@cache
def _repr_css() -> str:
    """Load the shared CSS used by entity HTML representations."""
    css = importlib.resources.files("mammos_entity").joinpath(
        "_entity_collection_repr.css"
    )
    return f"<style>{css.read_text(encoding='utf-8')}</style>"
