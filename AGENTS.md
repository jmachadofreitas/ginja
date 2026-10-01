# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.12+ document engine: Markdown, HTML, Jinja2, TOML and CSS to HTML and PDF.
`docs/spec.md` is the design specification; `README.md` documents implemented behaviour.
Runtime code lives in `src/ginja/`:

- `project.py`: entry discovery, TOML loading, front matter, configuration precedence and
  the context namespaces;
- `templating.py`: the Jinja environment and the loader that keeps non-`.j2` files literal;
- `extensions.py`: loading `extensions/document.py`, `setup(env)`, `transform_data`;
- `markdown.py`: the one Markdown implementation (markdown-it-py);
- `build.py`: the pipeline, outer template, stylesheets, output paths, Jinja error mapping;
- `pdf.py`: WeasyPrint, imported lazily;
- `preview.py`: `ginja preview`, the polling watcher, the reload server;
- `cli.py`: the `ginja` command;
- `templates/default.html.j2` and `styles/default.css`: built-in defaults.

`examples/` holds three projects (letter, report, curriculum-vitae) that double as
integration tests. Tests live in `tests/`.

The engine must stay domain-independent. Anything about CVs (selection by tags, localized
fields, date formats) belongs in `examples/curriculum-vitae/extensions/document.py`, never
in `src/`.

## Build, Test, and Development Commands

```sh
just install-dev     # uv sync
just ci              # ruff check, ruff format --check, pytest
just test -k include # pass arguments through to pytest
just example-cv-all  # build all six CV variants into examples/curriculum-vitae/build/
just clean           # delete examples/*/build
```

## Coding Style & Naming Conventions

Four-space indentation, ruff (line length 100, isort), type annotations on public functions,
`pathlib.Path` for paths. Prefer small functions and plain dicts over classes and indirection.
Every failure a user can cause should raise `DocumentError(stage, message, path, line)` with
a project-relative path. Ruff is configured to skip Markdown, so it doesn't rewrite code
blocks in `docs/spec.md`.

## Testing Guidelines

Write pytest tests named `test_<behavior>()`. Use the `make_project` and `render_html`
fixtures from `tests/conftest.py` to create projects in `tmp_path`. Never build into the
checkout from tests: pass `output=tmp_path / ...` when building the examples. Changes to
include semantics, precedence or error locations need regression tests.

## Commits & Pull Requests

There is no commit history yet. Use concise imperative subjects, for example
`Add locale fallback for document.language`, and keep each commit focused.
