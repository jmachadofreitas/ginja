"""Outputs: file naming, stylesheets, outer templates, assets and determinism."""

import pytest

from ginja import DocumentError, build


def test_plain_markdown_builds_into_build_directory(make_project):
    root = make_project({"letter.md": "# Dear Jane\n\nThanks.\n"})
    (path,) = build(root / "letter.md", formats=["html"])
    assert path == root / "build" / "letter.html"
    html = path.read_text()
    assert html.startswith('<!doctype html>\n<html lang="en">')
    assert "<title>letter</title>" in html
    assert "<h1>Dear Jane</h1>" in html
    assert "Built-in stylesheet" in html  # no project CSS: the built-in default is inlined


def test_default_formats_are_html_and_pdf(make_project):
    root = make_project({"document.md": "x"})
    targets = [path.name for path in build(root, formats=None, output=None)]
    assert targets == ["document.html", "document.pdf"]


def test_conventional_stylesheet_replaces_the_default(render_html):
    html = render_html({"document.md": "x", "styles/document.css": "p { color: teal; }"})
    assert "p { color: teal; }" in html
    assert "Built-in stylesheet" not in html


def test_sibling_stylesheet_is_found(render_html):
    html = render_html({"letter.md": "x", "letter.css": "p { color: red; }"}, "letter.md")
    assert "p { color: red; }" in html


def test_style_list_may_extend_the_built_in_default(render_html):
    html = render_html(
        {
            "document.md": "x",
            "document.toml": "style = ['default.css', 'extra.css']\n",
            "styles/extra.css": "h1 > span { color: red; }",
        }
    )
    assert html.index("Built-in stylesheet") < html.index(
        "h1 > span { color: red; }"
    )  # not escaped


def test_missing_stylesheet_fails(make_project):
    root = make_project({"document.md": "x", "document.toml": "style = 'nope.css'\n"})
    with pytest.raises(DocumentError, match="stylesheet 'nope.css' not found"):
        build(root, formats=["html"])


def test_project_template_receives_content_and_context(render_html):
    html = render_html(
        {
            "document.md.j2": "# {{ document.title }}\n",
            "document.toml": "title = 'Report'\ntemplate = 'report'\n",
            "templates/report.html.j2": '<main data-title="{{ document.title }}">\n{{ content }}</main>\n',
        }
    )
    assert html == (
        '<main data-title="Report">\n<section id="report">\n<h1>Report</h1>\n</section>\n</main>\n'
    )


def test_project_default_template_overrides_the_built_in(render_html):
    html = render_html(
        {"document.md": "x", "templates/default.html.j2": "<article>{{ content }}</article>"}
    )
    assert html == "<article><p>x</p>\n</article>\n"


def test_generated_html_is_not_evaluated_again(render_html):
    html = render_html(
        {
            "document.md.j2": "{{ data.text.value }}",
            "data/text.toml": "value = '{{ 1 + 1 }}'\n",
        }
    )
    assert "<p>{{ 1 + 1 }}</p>" in html


def test_template_false_writes_the_fragment(render_html):
    html = render_html(
        {
            "document.html.j2": "<!doctype html>\n<p>{{ 1 + 1 }}</p>\n",
            "document.toml": "template = false\n",
        }
    )
    assert html == "<!doctype html>\n<p>2</p>\n"


def test_missing_template_fails(make_project):
    root = make_project({"document.md": "x", "document.toml": "template = 'cv'\n"})
    with pytest.raises(DocumentError, match="template 'cv.html.j2' not found"):
        build(root, formats=["html"])


def test_language_follows_the_selected_locale(render_html):
    html = render_html({"document.md": "x", "locales/de.toml": ""}, locale="de")
    assert '<html lang="de">' in html


def test_assets_are_copied_next_to_the_html(make_project):
    root = make_project(
        {
            "document.md": "![Logo](assets/logo.svg)\n",
            "assets/logo.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>",
        }
    )
    (path,) = build(root, formats=["html"])
    assert '<img src="assets/logo.svg" alt="Logo" />' in path.read_text()
    assert (root / "build" / "assets" / "logo.svg").is_file()


def test_output_names_carry_profile_and_locale(make_project):
    root = make_project(
        {
            "document.md": "x",
            "document.toml": "output = 'cv'\n",
            "profiles/data-science.toml": "",
            "locales/de.toml": "",
        }
    )
    (path,) = build(root, profile="data-science", locale="de", formats=["html"])
    assert path == root / "build" / "cv-data-science-de.html"


def test_explicit_output_selects_the_format(make_project, tmp_path):
    root = make_project({"document.md": "x"})
    (path,) = build(root, output=tmp_path / "out" / "custom.html")
    assert path == tmp_path / "out" / "custom.html"
    assert path.is_file()


def test_explicit_output_must_match_the_format(make_project):
    root = make_project({"document.md": "x"})
    with pytest.raises(DocumentError, match="does not match format"):
        build(root, output=root / "x.html", formats=["pdf"])
    with pytest.raises(DocumentError, match="cannot infer the format"):
        build(root, output=root / "x.docx")


def test_html_is_byte_identical_across_builds(make_project):
    root = make_project(
        {
            "document.md.j2": "{% for name, value in data.values.items() %}\n- {{ name }}: {{ value }}\n{% endfor %}\n",
            "data/values.toml": "b = 2\na = 1\n",
        }
    )
    (path,) = build(root, formats=["html"])
    first = path.read_bytes()
    build(root, formats=["html"])
    assert path.read_bytes() == first
