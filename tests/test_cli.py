"""The `ginja` command line."""

import pytest

from ginja import DocumentError
from ginja.cli import main, parse_overrides


def test_build_prints_written_files(make_project, capsys, monkeypatch):
    root = make_project({"document.md": "# Hi\n"})
    monkeypatch.chdir(root)
    assert main(["build", "--format", "html"]) == 0
    assert capsys.readouterr().out == "build/document.html\n"


def test_set_and_output_options(make_project, capsys, monkeypatch):
    root = make_project({"document.md.j2": "{{ document.title }} {{ document.meta.draft }}"})
    monkeypatch.chdir(root)
    status = main(
        [
            "build",
            "document.md.j2",
            "--set",
            "title=Hello World",
            "--set",
            "meta.draft=true",
            "-o",
            "out/x.html",
        ]
    )
    assert status == 0
    assert "<p>Hello World True</p>" in (root / "out" / "x.html").read_text()
    assert capsys.readouterr().out == "out/x.html\n"


def test_errors_name_stage_file_and_line(make_project, capsys, monkeypatch):
    root = make_project({"document.md.j2": "# Title\n\n{{ data.persn.name }}\n"})
    monkeypatch.chdir(root)
    assert main(["build", "--format", "html"]) == 1
    error = capsys.readouterr().err
    assert error.startswith("ginja: error [Jinja rendering] document.md.j2:3: undefined: ")
    assert "persn" in error


def test_init_writes_a_sample_that_builds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "letter"]) == 0
    assert capsys.readouterr().out == "letter/document.md\nletter/styles/document.css\n"
    stylesheet = (tmp_path / "letter" / "styles" / "document.css").read_text()
    assert stylesheet.startswith(":root {")
    assert "Built-in stylesheet" in stylesheet
    monkeypatch.chdir(tmp_path / "letter")
    assert main(["build", "--format", "html"]) == 0
    html = (tmp_path / "letter" / "build" / "document.html").read_text()
    assert "<h1>Title</h1>" in html
    assert "<h2>Section</h2>" in html
    assert "<ul>" in html


def test_init_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    (tmp_path / "document.md").write_text("keep\n")
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 1
    error = capsys.readouterr().err
    assert error.startswith("ginja: error [init] ")
    assert "refusing to overwrite document.md" in error
    assert (tmp_path / "document.md").read_text() == "keep\n"
    assert not (tmp_path / "styles" / "document.css").exists()


def test_parse_overrides():
    overrides = parse_overrides(
        ["title=My Title", "pages=3", "meta.date=2026-10-01", "tags=['a', 'b']"]
    )
    assert overrides["title"] == "My Title"
    assert overrides["pages"] == 3
    assert str(overrides["meta"]["date"]) == "2026-10-01"
    assert overrides["tags"] == ["a", "b"]
    with pytest.raises(DocumentError, match="KEY=VALUE"):
        parse_overrides(["title"])
