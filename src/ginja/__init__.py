"""Programmable Markdown/Jinja document engine: Markdown, HTML, Jinja2, TOML and CSS to HTML
and PDF."""

from .build import build
from .errors import DocumentError

__version__ = "0.1.0"
__all__ = ["DocumentError", "__version__", "build"]
