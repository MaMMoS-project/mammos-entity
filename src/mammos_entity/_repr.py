"""Helpers for notebook HTML representations."""

from __future__ import annotations

import importlib.resources
from functools import cache


@cache
def _repr_css() -> str:
    """Load the shared CSS used by entity HTML representations."""
    css = importlib.resources.files("mammos_entity").joinpath(
        "_entity_collection_repr.css"
    )
    return f"<style>{css.read_text(encoding='utf-8')}</style>"
