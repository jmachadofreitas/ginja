"""Jinja processing and include semantics: the file extension decides how a file is processed."""

import pytest

from ginja import DocumentError, build


def test_md_include_is_never_evaluated_as_jinja(render_html):
    html = render_html(
        {
            "document.md.j2": '{% include "content/intro.md" %}',
            "content/intro.md": "Literal {{ price }} and {% if x %} and {# note #}.\n",
        }
    )
    assert "<p>Literal {{ price }} and {% if x %} and {# note #}.</p>" in html


def test_md_j2_include_is_evaluated(render_html):
    html = render_html(
        {
            "document.md.j2": '{% include "content/sum.md.j2" %}',
            "content/sum.md.j2": "Sum: {{ 2 + 3 }}\n",
        }
    )
    assert "<p>Sum: 5</p>" in html


def test_nested_includes(render_html):
    html = render_html(
        {
            "document.md.j2": '# Report\n\n{% include "content/body.md.j2" %}',
            "content/body.md.j2": 'Body.\n\n{% include "content/fragments/table.md" %}',
            "content/fragments/table.md": "| a | b |\n|---|---|\n| 1 | 2 |\n",
        }
    )
    assert "<p>Body.</p>" in html
    assert "<td>1</td>" in html


def test_includes_compose_source_before_one_markdown_pass(render_html):
    html = render_html(
        {
            "document.md.j2": '- first\n{% include "content/more.md" %}',
            "content/more.md": "- second\n",
        }
    )
    assert "<ul>\n<li>first</li>\n<li>second</li>\n</ul>" in html


def test_includes_separated_by_a_blank_line_stay_separate_blocks(render_html):
    html = render_html(
        {
            "document.md.j2": '{% include "content/a.md" %}\n\n{% include "content/b.md" %}',
            "content/a.md": "Alpha",  # no trailing newline: the loader adds one
            "content/b.md": "Beta",
        }
    )
    assert "<p>Alpha</p>\n<p>Beta</p>" in html


def test_html_include_is_literal_inside_markdown(render_html):
    html = render_html(
        {
            "document.md.j2": 'Intro.\n\n{% include "content/box.html" %}',
            "content/box.html": '<div class="box">{{ not jinja }} & *not markdown*</div>\n',
        }
    )
    assert '<div class="box">{{ not jinja }} & *not markdown*</div>' in html


def test_loops_generate_tight_markdown_lists(render_html):
    html = render_html(
        {
            "document.md.j2": """
            {% set items = [{"name": "A", "description": "first"}, {"name": "B", "description": "second"}] %}
            {% for item in items %}
            - **{{ item.name }}** — {{ item.description }}
            {% endfor %}
        """,
        }
    )
    expected = (
        "<ul>\n<li><strong>A</strong> — first</li>\n<li><strong>B</strong> — second</li>\n</ul>"
    )
    assert expected in html


def test_autoescape_is_on_for_html_and_off_for_markdown(render_html):
    overrides = {"value": "<em>x</em>"}
    files = {"page.md.j2": "{{ document.value }}", "page.html.j2": "<p>{{ document.value }}</p>"}
    markdown = render_html(files, "page.md.j2", overrides=overrides)
    html = render_html(files, "page.html.j2", overrides=overrides)
    assert "<p><em>x</em></p>" in markdown
    assert "<p>&lt;em&gt;x&lt;/em&gt;</p>" in html


def test_macros_from_templates_macros(render_html):
    html = render_html(
        {
            "document.md.j2": """
            {% from "macros/common.html.j2" import badge %}
            Team: {{ badge("R&D") }}
        """,
            "templates/macros/common.html.j2": """
            {% macro badge(label) %}<span class="badge">{{ label }}</span>{% endmacro %}
        """,
        }
    )
    assert '<p>Team: <span class="badge">R&amp;D</span></p>' in html


def test_template_inheritance(render_html):
    html = render_html(
        {
            "document.md.j2": '{% extends "base.md.j2" %}\n{% block main %}Child text.{% endblock %}',
            "templates/base.md.j2": "# Base\n\n{% block main %}{% endblock %}\n",
        }
    )
    assert "<h1>Base</h1>\n<p>Child text.</p>" in html


def test_missing_include_names_the_including_file_and_line(make_project):
    root = make_project(
        {
            "document.md.j2": '# Title\n\n{% include "content/body.md.j2" %}\n',
            "content/body.md.j2": 'Text.\n\n{% include "content/missing.md" %}\n',
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.stage, error.path, error.line) == ("include resolution", "content/body.md.j2", 3)
    assert "content/missing.md" in error.message


def test_parent_directory_includes_are_rejected(make_project):
    root = make_project({"doc/document.md.j2": '{% include "../secret.md" %}', "secret.md": "x"})
    with pytest.raises(DocumentError, match="include resolution"):
        build(root / "doc", formats=["html"])


def test_undefined_variable_fails_with_location(make_project):
    root = make_project({"document.md.j2": "+++\ntitle = 'T'\n+++\n\n{{ document.titel }}\n"})
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.stage, error.path, error.line) == ("Jinja rendering", "document.md.j2", 5)
    assert "titel" in error.message


def test_syntax_error_in_include_names_that_file(make_project):
    root = make_project(
        {
            "document.md.j2": '{% include "content/bad.md.j2" %}',
            "content/bad.md.j2": "ok\n{% if %}\n",
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    assert (caught.value.path, caught.value.line) == ("content/bad.md.j2", 2)


def test_errors_inside_macros_list_the_call_chain(make_project):
    root = make_project(
        {
            "document.md.j2": '# Title\n\n{% include "content/body.md.j2" %}\n',
            "content/body.md.j2": (
                '{% from "macros/m.html.j2" import show %}\nText.\n{{ show(data.missing) }}\n'
            ),
            "templates/macros/m.html.j2": "{% macro show(value) %}\n<b>{{ value }}</b>\n{% endmacro %}\n",
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.path, error.line) == ("templates/macros/m.html.j2", 2)
    assert error.message.endswith("(via content/body.md.j2:3, document.md.j2:3)")
