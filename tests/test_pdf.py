"""PDF output through WeasyPrint."""

import pytest

from ginja import DocumentError, build

pytest.importorskip("weasyprint")

LOGO = "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40'><rect width='40' height='40'/></svg>"


def test_pdf_is_written_with_assets_resolved_from_the_root(make_project):
    root = make_project(
        {"letter.md": "# Letter\n\n![Logo](assets/logo.svg)\n", "assets/logo.svg": LOGO}
    )
    (path,) = build(root / "letter.md", formats=["pdf"])
    assert path == root / "build" / "letter.pdf"
    # An unresolvable image fails the build (see below), so success means the logo was found.
    assert path.read_bytes().startswith(b"%PDF-")


def test_missing_asset_fails_the_pdf_build(make_project):
    root = make_project({"document.md": "![Logo](assets/missing.svg)\n"})
    with pytest.raises(DocumentError, match=r"\[PDF rendering\].*missing\.svg"):
        build(root, formats=["pdf"])


def test_pdf_is_byte_identical_across_builds(make_project):
    root = make_project({"document.md": "# Title\n\nSome text with *emphasis*.\n"})
    (path,) = build(root, formats=["pdf"])
    first = path.read_bytes()
    build(root, formats=["pdf"])
    assert path.read_bytes() == first
