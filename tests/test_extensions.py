"""Project extensions: `setup(env)` for presentation, `transform_data(context)` for data."""

import pytest

from ginja import DocumentError, build


def test_setup_registers_filters_globals_and_tests(render_html):
    html = render_html(
        {
            "document.md.j2": "{{ 'x' | shout }} {{ greeting }} {{ 'yes' if 4 is even_number else 'no' }}",
            "extensions/document.py": """
            def setup(env):
                env.filters["shout"] = lambda value: value.upper() + "!"
                env.globals["greeting"] = "hello"
                env.tests["even_number"] = lambda value: value % 2 == 0
        """,
        }
    )
    assert "<p>X! hello yes</p>" in html


def test_transform_data_sees_profile_and_locale(render_html):
    html = render_html(
        {
            "document.md.j2": "{% for item in data.selected %}\n- {{ item }}\n{% endfor %}\n",
            "data/catalog.toml": """
                [[items]]
                id = "a"
                name.en = "Apple"
                name.de = "Apfel"

                [[items]]
                id = "b"
                name.en = "Pear"
                name.de = "Birne"
            """,
            "profiles/only-b.toml": "ids = ['b']\n",
            "locales/de.toml": "",
            "extensions/document.py": """
                def transform_data(context):
                    language = context["build"]["locale"]
                    wanted = context["profile"]["ids"]
                    items = context["data"]["catalog"]["items"]
                    context["data"]["selected"] = [
                        item["name"][language] for item in items if item["id"] in wanted
                    ]
                    return context
            """,
        },
        profile="only-b",
        locale="de",
    )
    assert "<ul>\n<li>Birne</li>\n</ul>" in html


def test_sibling_helper_modules_are_importable(render_html):
    html = render_html(
        {
            "document.md.j2": "{{ data.answer }}",
            "extensions/document_engine_test_helper.py": "ANSWER = 42\n",
            "extensions/document.py": """
            from document_engine_test_helper import ANSWER

            def transform_data(context):
                context["data"]["answer"] = ANSWER
                return context
        """,
        }
    )
    assert "<p>42</p>" in html


def test_transform_must_return_the_context(make_project):
    root = make_project(
        {
            "document.md.j2": "x",
            "extensions/document.py": "def transform_data(context):\n    context['data']['x'] = 1\n",
        }
    )
    with pytest.raises(DocumentError, match="must return the context mapping, got NoneType"):
        build(root, formats=["html"])


def test_import_failure_names_the_extension_line(make_project):
    root = make_project(
        {
            "document.md.j2": "x",
            "extensions/document.py": "import os\n\nraise RuntimeError('broken setup')\n",
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.stage, error.path, error.line) == (
        "extension loading",
        "extensions/document.py",
        3,
    )
    assert "RuntimeError: broken setup" in error.message


def test_transform_failure_is_a_data_transformation_error(make_project):
    root = make_project(
        {
            "document.md.j2": "x",
            "extensions/document.py": "def transform_data(context):\n    return context['data']['missing']\n",
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.stage, error.path, error.line) == (
        "data transformation",
        "extensions/document.py",
        2,
    )


def test_failing_filter_points_at_the_template_line(make_project):
    root = make_project(
        {
            "document.md.j2": "ok\n\n{{ 1 | explode }}\n",
            "extensions/document.py": """
            def explode(value):
                raise ValueError("bad value")

            def setup(env):
                env.filters["explode"] = explode
        """,
        }
    )
    with pytest.raises(DocumentError) as caught:
        build(root, formats=["html"])
    error = caught.value
    assert (error.stage, error.path, error.line) == ("Jinja rendering", "document.md.j2", 3)
    assert "ValueError: bad value" in error.message
