# Ginja 🍒

Build HTML and PDF documents with Markdown, Jinja2, and CSS.

A small, programmable document engine built on existing languages: Markdown for prose, HTML
for structure, Jinja2 for composition and logic, TOML for configuration and data, CSS for
layout, and Python for extensions. It renders HTML, and PDF from that HTML through
[WeasyPrint](https://weasyprint.org). The engine is domain-independent. The
[CV example](examples/curriculum-vitae) shows a domain built on top of it.

The design is specified in [docs/spec.md](docs/spec.md). This README describes what is
implemented: milestones 0.1–0.5 of the spec.

## Using it for your own documents

There are two ways to use the engine, depending on how long a document lives.

### Quick documents: a global `ginja` command

For letters, handouts and one-off reports, install `ginja` once as a uv tool:

```bash
uv tool install --editable ~/Code/Portfolio/document-engine
```

`ginja` then works in any folder. A document is just a directory (`letter.md`, or
`document.md.j2` with `document.toml` and friends) with no Python project around it.
`--editable` makes changes to the engine checkout apply immediately.

`extensions/document.py` runs in the tool's environment. It can import what the engine
ships (Jinja2, markdown-it-py, …) plus any packages added with
`uv tool install --with <package>`.

### Long-lived documents: their own project that pins the engine

Give a document you will keep rebuilding, such as a CV, its own repository with a
`pyproject.toml`:

```toml
[project]
name = "cv"
version = "0"
requires-python = ">=3.12"
dependencies = ["ginja"]

[tool.uv]
package = false  # a document, not a Python package

[tool.uv.sources]
ginja = { path = "../document-engine", editable = true }
# Once the tool is tagged:
# ginja = { git = "https://github.com/jmachadofreitas/ginja", tag = "v0.1.0" }
```

```bash
uv run ginja build --profile data-science --locale de
```

- `uv.lock` pins the engine version, so the document still renders the same later.
- The document's extensions can use extra libraries listed in its own `dependencies`.
- Personal data stays in that repository. The bundled
  [CV example](examples/curriculum-vitae) is fictional; copy it as a starting point and
  replace the data.

### Requirements

PDF output needs Pango, which WeasyPrint uses for text layout. It is preinstalled on most
Linux desktops; on macOS, run `brew install pango`. See WeasyPrint's
[installation notes](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for
other platforms.

While writing, run `ginja preview`: it rebuilds on every save and reloads the page in the
browser. `ginja preview --format pdf` does the same for the PDF in your PDF viewer.

## Quick start

Start a document with the built-in A4 stylesheet:

```bash
ginja init my-letter             # document.md and styles/document.css
cd my-letter
ginja build                      # → build/document.html, build/document.pdf
```

`styles/document.css` starts with a `:root` block: type size in pt, line spacing, and
margins in cm. `#` is the title, `##` a section, `###` a subsection. A single Markdown file
with no stylesheet still uses the copy shipped with the tool:

```bash
ginja build letter.md            # → build/letter.html, build/letter.pdf
```

Add complexity only when you need it:

```text
letter.md                                     plain Markdown
letter.md + letter.css                        your own stylesheet
document.md.j2 + document.toml                Jinja and configuration
document.md.j2 + content/ data/ templates/…   multi-file project
```

## File types

The extension says how a file is processed. A final `.j2` always means "Jinja first".

| File | Processing |
|---|---|
| `*.md` | Markdown, never Jinja |
| `*.md.j2` | Jinja → Markdown |
| `*.html` | HTML, never Jinja |
| `*.html.j2` | Jinja → HTML |
| `*.css` | inlined into the HTML |
| `*.toml` | configuration or data |
| `extensions/document.py` | Python extension |

The pipeline is:

```text
source → Jinja (if .j2) → Markdown (if .md) → HTML fragment → outer template + CSS → HTML → PDF
```

## Project layout

None of these directories is required; each one becomes active when it exists.

```text
my-document/
├── document.md.j2          entry document (or document.md, document.html.j2, document.html)
├── document.toml           configuration → {{ document.* }}
├── content/                prose fragments, included with {% include "content/x.md" %}
├── data/                   data/<name>.toml → {{ data.<name>.* }}   (folder name: `data`)
├── profiles/               profiles/<name>.toml → {{ profile.* }}   (--profile)
├── locales/                locales/<code>.toml → {{ locale.* }}     (--locale)
├── templates/              outer HTML templates, e.g. default.html.j2
│   └── macros/             Jinja macros: {% from "macros/x.html.j2" import y %}
├── styles/                 CSS; styles/<stem>.css is picked up automatically
├── assets/                 images, fonts, …, referenced as assets/…
├── extensions/document.py  setup(env) and transform_data(context)
└── build/                  generated files only; safe to delete
```

`ginja build DIR` picks the first of `document.md.j2`, `document.md`, `document.html.j2` and
`document.html` in `DIR`. The **project root** is the directory that contains the entry
document.

## Composition and includes

Jinja includes are the composition mechanism. Template names resolve in a fixed order: the
project root first, then `templates/`, then the built-in templates. So
`"content/intro.md"` comes from the root and `"macros/cv.html.j2"` from `templates/`. Paths
containing `..` are rejected.

```jinja
# {{ document.title }}

{% include "content/introduction.md" %}

{% include "content/results.md.j2" %}
```

- Included files keep their extension's meaning. A `.md` or `.html` include is inserted
  verbatim, so `{{ … }}` inside it is never evaluated. A `.md.j2` include is rendered by
  Jinja.
- Includes compose **source text**. The entry's type decides the one final conversion, so
  Markdown included into a `.md.j2` document is converted to HTML once, at the end, and
  nothing is rendered twice. Nested includes work.
- HTML is valid inside Markdown. CommonMark ends an HTML block at the first blank line, so
  keep HTML fragments and macro output free of blank lines. The Markdown is not processed
  inside an HTML block.

## The rendering context

Templates see a small, explicit set of names:

| Name | Contents |
|---|---|
| `document` | configuration (see below) |
| `profile` | the selected `profiles/<name>.toml`, or `{}` |
| `locale` | the selected `locales/<code>.toml`, or `{}` |
| `data` | every `data/*.toml`, keyed by file stem. With `data = "facts"` the folder is `facts/` and the name `facts` |
| `build` | `entry`, `profile` and `locale`: the entry file name and the selected names |

The outer template also receives `content` (the rendered fragment) and `styles` (the CSS
texts). The engine reads only a few `document` keys (see below). Every other key, in every
namespace, is passed through for your templates and extensions.

`a.b` on a TOML table always means the key `b`, even when it is named like a dict method,
so `data.inventory.items` returns your `items` array.

## Configuration

`document` is merged from these layers, later ones winning; tables merge key by key:

```text
built-in defaults < document.toml < profile's [document] table < front matter < --set
```

Front matter is TOML between `+++` lines at the top of the entry document:

```markdown
+++
title = "Example"
+++

# {{ document.title }}
```

Keys the engine reads:

| Key | Default | Meaning |
|---|---|---|
| `title` | entry stem | `<title>` and PDF metadata |
| `language` | `"en"` | `<html lang>` when no locale is selected |
| `template` | `"default"` | outer template; `"cv"` means `cv.html.j2`; `false` writes the fragment as-is |
| `style` | auto | a name or a list, found in `styles/`, the root, or the built-in styles (`default.css`). Without it: `styles/<stem>.css`, then `<stem>.css`, then the built-in default |
| `output` | entry stem | base name of the generated files |
| `profile`, `locale` | none | default selections, overridden by `--profile` / `--locale` |
| `data` | `"data"` | folder of TOML data files and their name in templates: `data = "facts"` loads `facts/*.toml` as `facts.*` |

## Profiles and locales

Profiles and locales are independent. Any combination is valid:

```bash
ginja build document.md.j2 --profile data-science --locale de
```

A profile's top-level keys become `profile.*`. The engine doesn't interpret them; your
templates and extensions do. A `[document]` table in a profile overrides document settings
such as `title`, `template`, `style` or the default `locale`.

Output files are named `build/<output>[-<profile>][-<locale>].{html,pdf}`, so variants don't
overwrite each other.

## Extensions

`extensions/document.py` is trusted project code with two optional hooks:

```python
def setup(env):
    """Presentation: register Jinja filters, globals and tests."""
    env.filters["format_date"] = format_date


def transform_data(context):
    """Preprocessing: select, localize and order data before any template runs."""
    context["data"]["items"] = sorted(context["data"]["catalog"]["items"], key=...)
    return context
```

`transform_data` receives the whole context as plain dicts, including `profile`, `locale`
and `build`. It must return the context. Other modules in `extensions/` can be imported from
`document.py`.

The engine adds one filter of its own: `markdown`, which renders a Markdown string (for
example, a TOML description inside an HTML template) to HTML; `markdown(inline=true)` skips
the paragraph wrapper.

## Templates, CSS and assets

When there is no `templates/default.html.j2`, the built-in shell is used: `<head>` with the
title and inlined CSS, and `<body>{{ content }}</body>`. A project template must render
`content`, and should render `styles`:

```jinja
{% for css in styles %}<style>{{ css }}</style>{% endfor %}
```

CSS is the only styling and page-layout system: `@page`, margins, page breaks, and running
headers and footers through margin boxes. The built-in sheet styles the HTML Markdown
already emits (`h1` for `#`, `h2` for `##`, and so on). Edit its `:root` block to change
the type size, line spacing, page margins and page numbers (`--page-numbers`, off by
default). To keep the built-in sheet and change only some values, list it first:
`style = ["default.css", "document.css"]`, and set the `:root` values you want in
`styles/document.css`.

Write asset URLs relative to the project root, in HTML and in CSS alike: `assets/logo.svg`,
`url("assets/fonts/x.woff2")`. The PDF resolves them against the project root. The HTML build
copies `assets/` next to the HTML file, so the same URLs work there too.

## CLI

```bash
ginja init [DIR]                         # document.md and styles/document.css
ginja build [ENTRY]                      # HTML and PDF into build/
ginja build ENTRY --format html|pdf|all
ginja build ENTRY --profile NAME --locale CODE
ginja build ENTRY --output build/custom.pdf   # the format comes from the suffix
ginja build ENTRY --set title="Draft" --set meta.draft=true   # VALUE is TOML, else a string
ginja preview [ENTRY]                    # rebuild HTML on every save, serve on 127.0.0.1:5500
ginja preview ENTRY --format pdf         # rebuild the PDF on every save, open it once
ginja preview ENTRY --profile NAME --locale CODE --port 5501 --no-open
```

`ginja preview` writes the same files as `ginja build` and watches the whole project except
`build/` and hidden directories. In the browser, a failed build shows the error until the
next good one; the PDF keeps its last good version. It needs no extra packages.

Errors name the stage, the file and the line, and the build stops:

```text
ginja: error [TOML loading] data/person.toml:3: Invalid value (at line 3, column 9)
ginja: error [include resolution] content/skills.md.j2:7: cannot find content/missing.md in the project root, templates/ or the built-in templates (via document.md.j2:5)
ginja: error [Jinja rendering] templates/macros/cv.html.j2:11: undefined: 'dict object' has no attribute 'companyy' (via content/experience.md.j2:5, document.md.j2:5)
```

The location is the innermost template line; "via" lists the templates that included or called
it, innermost first. An undefined value passed to a macro fails inside the macro, so the call
site is usually the first "via" entry.

WeasyPrint warnings, such as unsupported CSS, are printed as `ginja: warning …`. An image or
other resource that cannot be loaded fails the PDF build.

## Behaviour worth knowing

- **Undefined variables are errors.** Test optional values with `is defined` or `default()`.
  An inline `if` needs an `else`: write `{{ 'x' if flag else '' }}`.
- **Block tags don't leave blank lines** (`trim_blocks`, `lstrip_blocks`), so a `{% for %}`
  loop around `- item` lines produces a tight Markdown list. Separate block-level includes
  with a blank line, as you would separate paragraphs. Don't indent generated Markdown: four
  spaces make a code block.
- **Autoescaping** is on for `.html.j2` templates and macros, and off for `.md.j2`. Macros from
  an HTML file can safely be called from Markdown.
- **Markdown** is [markdown-it-py](https://markdown-it-py.readthedocs.io): CommonMark with raw
  HTML, tables, strikethrough and footnotes.
- **Heading sections.** A heading and the blocks after it, up to the next heading of the same
  or higher level, are wrapped in `<section id="...">`. The id is the heading text:
  `## Publications` becomes `publications`. A repeat becomes `publications-1`. Style that
  section from CSS, for example `#publications { font-size: 9pt; }`.
- **Explicit section ids.** End a heading with `{#id}`, as in Pandoc, to choose the id:
  `## Ausgewählte Publikationen {#publications}`. It doesn't change when the heading is
  renamed or translated. In `.j2` files write `{ #id }` with spaces, because `{#` starts a
  Jinja comment.
- **Builds are deterministic**: the same inputs give byte-identical HTML and PDF. Nothing
  reads the clock or embeds absolute paths. The PDF backend's font timestamps are pinned
  through `SOURCE_DATE_EPOCH`, and a value you set yourself is respected.

## Examples

| Example | Shows | Build |
|---|---|---|
| [letter](examples/letter) | one `.md` file, front matter, raw HTML, an asset, the built-in template and CSS | `just example-letter` |
| [report](examples/report) | `.md.j2` with `content/` includes (nested), `data/`, a filter, a transform, running footers | `just example-report` |
| [curriculum-vitae](examples/curriculum-vitae) | 3 profiles × 2 locales from one source, macros, a custom template, CV logic in an extension | `just example-cv-all` |

## Development

To work on the engine itself, from this checkout:

```bash
just install-dev    # uv sync: the engine and its dev tools in .venv
just ci             # ruff + pytest
just --list         # all recipes
just cli build examples/report --format html   # run ginja from the checkout
```

## Not implemented yet

The following are deferred, as the spec says, until a concrete use case needs them: a
generic build matrix (`ginja build-all`; the CV builds its variants with a justfile loop),
Pandoc, DOCX/EPUB, schema validation, and the other items listed in spec §32.
