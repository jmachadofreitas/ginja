from pathlib import Path
from textwrap import dedent

import pytest

from ginja import build


@pytest.fixture
def make_project(tmp_path):
    """Write `{relative path: text}` into a fresh project directory and return its root."""

    def make(files: dict[str, str]) -> Path:
        for name, text in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dedent(text).lstrip("\n"), encoding="utf-8")
        return tmp_path

    return make


@pytest.fixture
def render_html(make_project):
    """Build a project to HTML only and return the written HTML text."""

    def render(files: dict[str, str], entry: str = ".", **options) -> str:
        root = make_project(files)
        (path,) = build(root / entry, formats=["html"], **options)
        return path.read_text(encoding="utf-8")

    return render
