"""Project discovery, configuration precedence, front matter and the context namespaces."""

import pytest

from ginja import DocumentError
from ginja.project import find_project, load_context


def context_of(root, entry=".", **options):
    return load_context(find_project(root / entry), **options)


def test_precedence_chain(make_project):
    root = make_project(
        {
            "document.md.j2": "+++\nc = 'front'\nd = 'front'\n+++\nBody\n",
            "document.toml": "a = 'toml'\nb = 'toml'\nc = 'toml'\nd = 'toml'\nprofile = 'p'\n",
            "profiles/p.toml": "[document]\nb = 'profile'\nc = 'profile'\nd = 'profile'\n",
        }
    )
    document = context_of(root, overrides={"d": "cli"})["document"]
    assert document["language"] == "en"  # built-in default
    assert [document[key] for key in "abcd"] == ["toml", "profile", "front", "cli"]


def test_defaults_derive_from_the_entry_stem(make_project):
    root = make_project({"letter.md": "Hi"})
    document = context_of(root, "letter.md")["document"]
    assert (document["title"], document["output"], document["template"]) == (
        "letter",
        "letter",
        "default",
    )


def test_tables_merge_key_by_key(make_project):
    root = make_project(
        {
            "document.md": "+++\n[meta]\nb = 3\n+++\n",
            "document.toml": "[meta]\na = 1\nb = 2\n",
        }
    )
    assert context_of(root)["document"]["meta"] == {"a": 1, "b": 3}


def test_profile_locale_data_and_build_are_separate_namespaces(make_project):
    root = make_project(
        {
            "document.md.j2": "x",
            "document.toml": "title = 'Doc'\nlocale = 'en'\n",
            "profiles/short.toml": "title = 'Short variant'\ninclude_tags = ['a']\n",
            "locales/en.toml": "experience = 'Experience'\n",
            "data/person.toml": "name = 'Jane Example'\n",
        }
    )
    context = context_of(root, profile="short")
    assert context["document"]["title"] == "Doc"
    assert context["profile"] == {"title": "Short variant", "include_tags": ["a"]}
    assert context["locale"] == {"experience": "Experience"}
    assert context["data"] == {"person": {"name": "Jane Example"}}
    assert context["build"] == {"entry": "document.md.j2", "profile": "short", "locale": "en"}


def test_cli_locale_overrides_the_configured_one(make_project):
    root = make_project(
        {
            "document.md": "x",
            "document.toml": "locale = 'en'\n",
            "locales/en.toml": "present = 'present'\n",
            "locales/de.toml": "present = 'heute'\n",
        }
    )
    assert context_of(root, locale="de")["locale"] == {"present": "heute"}


def test_profile_may_choose_the_default_locale(make_project):
    root = make_project(
        {
            "document.md": "x",
            "profiles/kunde.toml": "[document]\nlocale = 'de'\n",
            "locales/de.toml": "present = 'heute'\n",
        }
    )
    context = context_of(root, profile="kunde")
    assert context["build"]["locale"] == "de"
    assert context["profile"] == {}


def test_unknown_profile_lists_the_available_ones(make_project):
    root = make_project({"document.md": "x", "profiles/a.toml": "", "profiles/b.toml": ""})
    with pytest.raises(DocumentError, match="unknown profile 'c'; available: a, b"):
        context_of(root, profile="c")


def test_unknown_locale_without_locales_directory(make_project):
    root = make_project({"document.md": "x"})
    with pytest.raises(DocumentError, match="unknown locale 'de'; available: none"):
        context_of(root, locale="de")


def test_malformed_toml_names_file_and_line(make_project):
    root = make_project({"document.md": "x", "data/person.toml": "name = 'Jane'\ncity = \n"})
    with pytest.raises(DocumentError) as caught:
        context_of(root)
    assert (caught.value.stage, caught.value.path, caught.value.line) == (
        "TOML loading",
        "data/person.toml",
        2,
    )


def test_malformed_front_matter_reports_the_file_line(make_project):
    root = make_project({"document.md": "+++\ntitle = 'ok'\nauthor =\n+++\n"})
    with pytest.raises(DocumentError) as caught:
        context_of(root)
    assert (caught.value.path, caught.value.line) == ("document.md", 3)


def test_invalid_settings_fail_as_configuration_errors(make_project):
    root = make_project({"document.md": "x", "document.toml": "template = 3\n"})
    with pytest.raises(DocumentError, match="template must be"):
        context_of(root)


def test_directory_entry_prefers_the_jinja_document(make_project):
    root = make_project({"document.md": "plain", "document.md.j2": "jinja"})
    project = find_project(root)
    assert (project.entry.name, project.kind, project.stem) == (
        "document.md.j2",
        ".md.j2",
        "document",
    )


def test_directory_without_entry_document(make_project):
    root = make_project({"notes.txt": "x"})
    with pytest.raises(DocumentError, match="no entry document"):
        find_project(root)


def test_unsupported_entry_type(make_project):
    root = make_project({"notes.txt": "x"})
    with pytest.raises(DocumentError, match="unsupported entry type"):
        find_project(root / "notes.txt")


def test_toml_keys_named_like_dict_methods(render_html):
    html = render_html(
        {
            "document.md.j2": "{{ data.inventory.items | join(', ') }} / {{ data.inventory.values }}",
            "data/inventory.toml": "items = ['pen', 'ink']\nvalues = 'honesty'\n",
        }
    )
    assert "<p>pen, ink / honesty</p>" in html


def test_front_matter_feeds_the_document_namespace(render_html):
    html = render_html({"document.md.j2": "+++\ntitle = 'Example'\n+++\n# {{ document.title }}\n"})
    assert "<title>Example</title>" in html
    assert "<h1>Example</h1>" in html
    assert "+++" not in html


def test_data_setting_renames_folder_and_namespace(render_html):
    html = render_html(
        {
            "document.md.j2": "{{ facts.person.name }}\n",
            "document.toml": 'data = "facts"\n',
            "facts/person.toml": "name = 'Jane Example'\n",
            "data/ignored.toml": "x = \n",  # not loaded: the folder is facts/
        }
    )
    assert "Jane Example" in html


@pytest.mark.parametrize("name", ["profile", "build", "my-facts", "", 3])
def test_data_setting_rejects_reserved_or_invalid_names(make_project, name):
    root = make_project({"document.md": "x"})
    with pytest.raises(DocumentError) as caught:
        context_of(root, overrides={"data": name})
    assert caught.value.stage == "configuration"
    assert "data must be a folder name" in caught.value.message
