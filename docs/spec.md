# Programmable Markdown/Jinja Document Engine

## 1. Purpose

Build a lightweight, programmable document-generation system using established technologies rather than introducing a new document language.

The system must scale from:

```text
plain Markdown
```

to:

```text
Markdown
+ HTML
+ Jinja2
+ includes
+ TOML metadata/data
+ multiple files
+ profiles/locales
+ Python extensions
```

The initial implementation targets documents such as:

- letters
- CVs
- reports
- proposals
- invoices
- handouts
- simple technical or business documents

The first downstream application will be a separate CV-generation project capable of producing tailored CVs for different roles and languages.

The rendering engine itself must remain domain-independent.

---

# 2. Core Technologies

The system uses:

- Markdown for prose
- HTML for explicit structure
- Jinja2 for templating, composition, and logic
- CSS for presentation and print layout
- TOML for metadata, configuration, and structured data
- Python for extension logic
- HTML as the canonical rendered representation

Initial output formats:

```text
HTML
PDF
```

PDF generation is performed from rendered HTML/CSS using an HTML-to-PDF engine.

Pandoc is not required by the core implementation.

---

# 3. Design Principles

## 3.1 Progressive complexity

The smallest valid project is:

```text
document.md
```

It must render without configuration, templates, metadata, or project scaffolding.

Users add complexity only when required.

Examples:

```text
document.md
```

then:

```text
document.md
document.css
```

then:

```text
document.md.j2
document.toml
```

then:

```text
document.md.j2
content/
data/
templates/
styles/
...
```

The simple case must remain simple.

---

## 3.2 Existing languages first

Do not invent syntax where Markdown, HTML, Jinja2, CSS, TOML, or Python already provide an adequate solution.

Use:

```jinja
{% if condition %}
...
{% endif %}
```

rather than introducing another conditional syntax.

Use Jinja includes rather than introducing a custom include directive.

Use CSS rather than creating a page-layout DSL.

---

## 3.3 File names describe processing

Processing must be explicit from the file extension.

Supported source conventions:

```text
*.md       pure Markdown
*.md.j2    Jinja2 → Markdown

*.html     pure HTML
*.html.j2  Jinja2 → HTML

*.css      CSS

*.toml     configuration or structured data

*.py       Python extensions
```

A `.md` file must never be implicitly evaluated as Jinja.

A `.md.j2` file is always evaluated as Jinja before Markdown processing.

Likewise:

```text
foo.html.j2
```

means:

```text
Jinja2 → HTML
```

The final `.j2` suffix consistently indicates Jinja preprocessing.

---

## 3.4 HTML is the canonical representation

The principal processing pipeline is:

```text
source
  ↓
Jinja2, if .j2
  ↓
Markdown, if .md
  ↓
HTML fragment
  ↓
outer HTML template
  ↓
CSS
  ↓
HTML
  ↓
PDF renderer, if requested
```

Generated HTML should remain inspectable and independently useful.

---

## 3.5 Jinja runs before Markdown

For:

```text
document.md.j2
```

processing is:

```text
Jinja2 → Markdown → HTML
```

This permits Jinja to generate natural Markdown:

```jinja
{% for item in items %}
- **{{ item.name }}** — {{ item.description }}
{% endfor %}
```

Jinja should not be applied again to the generated HTML.

---

## 3.6 Rendering and domain logic are separate

The engine knows about:

- documents
- source files
- configuration
- data
- profiles
- locales
- templates
- rendering

It does not know about:

- CV experience
- skills
- jobs
- employment relevance
- job applications
- ATS rules
- portfolio projects

Those concepts belong in projects built on top of the engine.

---

# 4. Recommended Project Structure

The system should be opinionated about project organization.

Official examples, documentation, defaults, and tooling should consistently use:

```text
my-document/
│
├── document.md.j2
├── document.toml
│
├── content/
│   ├── introduction.md
│   └── section.md.j2
│
├── data/
│   └── example.toml
│
├── profiles/
│   └── example.toml
│
├── locales/
│   ├── en.toml
│   └── de.toml
│
├── templates/
│   ├── default.html.j2
│   └── macros/
│       └── common.html.j2
│
├── styles/
│   └── document.css
│
├── assets/
│   └── logo.svg
│
├── extensions/
│   └── document.py
│
└── build/
```

No directory is mandatory unless its corresponding feature is used.

---

# 5. Naming Conventions

Use one conventional name per concept.

## Entry document

Preferred:

```text
document.md
document.md.j2
```

Other names remain valid when explicitly supplied:

```bash
ginja build letter.md.j2
```

---

## Project configuration

Use:

```text
document.toml
```

Do not use competing names such as:

```text
project.toml
config.toml
settings.toml
```

in official examples.

---

## Directories

Use:

```text
content/
data/
profiles/
locales/
templates/
templates/macros/
styles/
assets/
extensions/
build/
```

Avoid alternative official names such as:

```text
includes/
partials/
snippets/
static/
resources/
output/
dist/
```

Consistency is preferred over flexibility in documentation.

---

# 6. Directory Semantics

## `content/`

Contains authored document material and document fragments.

Examples:

```text
content/introduction.md
content/history.md
content/results.md.j2
```

Content belongs here when it is primarily document prose.

---

## `data/`

Contains structured source data.

Preferred initial format:

```text
TOML
```

Examples:

```text
data/person.toml
data/company.toml
data/projects.toml
```

Data should describe information, not rendering.

---

## `profiles/`

Contains named build variants.

Examples:

```text
profiles/short.toml
profiles/customer-a.toml
profiles/data-science.toml
```

Profiles modify selection or configuration for a particular output variant.

Profiles are generic engine functionality and must not contain domain-specific assumptions.

---

## `locales/`

Contains language-specific values.

Examples:

```text
locales/en.toml
locales/de.toml
```

Locales are independent from profiles.

---

## `templates/`

Contains structural HTML/Jinja templates.

Example:

```text
templates/default.html.j2
```

Templates generally define the outer HTML structure.

---

## `templates/macros/`

Contains reusable Jinja macros.

Examples:

```text
templates/macros/common.html.j2
templates/macros/address.html.j2
```

Macros should be used for reusable presentation logic.

---

## `styles/`

Contains CSS.

Default convention:

```text
styles/document.css
```

---

## `assets/`

Contains static resources:

```text
images
SVG
logos
fonts
other files referenced by the document
```

---

## `extensions/`

Contains optional Python code extending the Jinja environment or data-processing pipeline.

Conventional project extension:

```text
extensions/document.py
```

---

## `build/`

Contains generated files only.

Example:

```text
build/document.html
build/document.pdf
```

The directory must be safe to delete entirely.

Generated and source files should not be mixed by default.

---

# 7. Minimal Projects

## Plain Markdown

```text
letter/
└── letter.md
```

Build:

```bash
ginja build letter.md
```

---

## Markdown with CSS

```text
letter/
├── document.md
└── styles/
    └── document.css
```

---

## Jinja document

```text
letter/
├── document.md.j2
└── document.toml
```

---

## Multi-file document

```text
report/
├── document.md.j2
├── document.toml
└── content/
    ├── introduction.md
    ├── findings.md
    └── conclusion.md
```

---

# 8. Markdown

The engine must support a documented Markdown implementation with at least:

- headings
- paragraphs
- emphasis
- lists
- links
- images
- fenced code blocks
- tables
- footnotes
- raw HTML

Raw HTML passthrough is required.

Example:

```markdown
## Contact

<div class="contact">
Jane Example  
Berlin, Germany
</div>
```

The exact Markdown library may be replaceable internally, but only one implementation needs first-class support initially.

---

# 9. HTML

HTML is a first-class escape hatch and authoring format.

Users may:

- embed HTML inside Markdown
- use pure `.html` fragments
- use `.html.j2` templates

The engine should avoid unnecessary rewriting of user-authored HTML.

---

# 10. Document Composition

Jinja includes are the primary composition mechanism.

Example:

```jinja
# {{ document.title }}

{% include "content/introduction.md" %}

{% include "content/results.md.j2" %}

{% include "content/conclusion.md" %}
```

No custom include syntax is required.

Nested includes must work.

Example:

```text
document.md.j2
    ↓
content/body.md.j2
    ↓
content/fragments/table.md
```

Path resolution should be deterministic and project-root based.

---

# 11. Include Semantics

Included files must respect their extensions.

Conceptually:

```text
foo.md
    Markdown

foo.md.j2
    Jinja → Markdown

foo.html
    HTML

foo.html.j2
    Jinja → HTML
```

The implementation must prevent accidental double rendering.

For example, a `.md.j2` include should not have its Markdown processed separately and then be injected into Markdown as HTML unless that behavior is explicitly part of the include mechanism.

The preferred semantic model is that source composition occurs before the final Markdown conversion whenever compatible Markdown sources are included.

Mixed Markdown/HTML composition should still be possible because HTML is valid inside Markdown.

---

# 12. Document Configuration

The conventional configuration file is:

```text
document.toml
```

Example:

```toml
title = "Example Document"
author = "Jane Example"
language = "en"

template = "default"
style = "document.css"
```

Configuration values should be exposed through an explicit namespace:

```jinja
{{ document.title }}
{{ document.author }}
```

Avoid injecting configuration keys as arbitrary top-level Jinja globals.

---

# 13. Front Matter

TOML front matter may be supported for source-local metadata:

```markdown
+++
title = "Example"
author = "Jane Example"
+++

# {{ document.title }}
```

External `document.toml` is preferred for larger projects.

Configuration precedence:

```text
built-in defaults
    <
document.toml
    <
profile-specific document overrides
    <
front matter
    <
CLI overrides
```

Locales and content data should not be flattened into this precedence chain.

They remain separate namespaces.

---

# 14. Structured Data

Structured data is optional.

The conventional location is:

```text
data/
```

Example:

```toml
# data/person.toml

name = "Jane Example"
city = "Berlin"
email = "jane@example.com"
```

Expose this as:

```jinja
{{ data.person.name }}
{{ data.person.city }}
```

Nested TOML structures should map naturally to Python/Jinja objects.

No schema system is required initially.

---

# 15. Profiles

Profiles represent named document variants.

Example:

```text
profiles/
├── compact.toml
├── customer-a.toml
└── data-science.toml
```

Build:

```bash
ginja build document.md.j2 --profile compact
```

A profile may define:

- metadata overrides
- content selection configuration
- ordering configuration
- tags
- template selection
- stylesheet selection
- arbitrary project-specific variables

Example:

```toml
title = "Data Scientist"

include_tags = [
    "python",
    "machine-learning",
    "statistics"
]

projects = [
    "forecasting",
    "recommendation-system"
]
```

The engine does not interpret domain-specific keys such as `include_tags` or `projects`.

It loads them and exposes them to project logic.

Profile context should be available as:

```jinja
{{ profile.title }}
{{ profile.include_tags }}
```

---

# 16. Locales

Locales represent language-specific data and terminology.

Example:

```text
locales/
├── en.toml
└── de.toml
```

Build:

```bash
ginja build document.md.j2 --locale de
```

Example locale:

```toml
experience = "Berufserfahrung"
education = "Ausbildung"
present = "heute"
```

Accessible as:

```jinja
{{ locale.experience }}
```

Profiles and locales are independent dimensions.

Example:

```bash
ginja build document.md.j2 \
    --profile data-science \
    --locale de
```

must be valid.

---

# 17. Localized Structured Data

The engine should permit localized values in structured data but should not prescribe a domain-specific localization schema.

One supported convention may be:

```toml
title.en = "Demand Forecasting Platform"
title.de = "Plattform zur Nachfrageprognose"
```

Project-specific preprocessing may resolve this into:

```text
title = selected localized value
```

before templates render.

Automatic machine translation is outside scope.

---

# 18. Rendering Context

The Jinja context should remain explicit and predictable.

Recommended top-level namespaces:

```text
document
profile
locale
data
```

Potential engine metadata may be exposed separately if required:

```text
source
build
```

Avoid large implicit global namespaces.

A template should normally look like:

```jinja
# {{ document.title }}

{{ data.person.name }}

## {{ locale.experience }}
```

rather than relying on dozens of injected global variables.

---

# 19. Data Resolution

Projects may optionally preprocess structured data before Jinja rendering.

Recommended conceptual pipeline:

```text
raw data
   ↓
profile selection
   ↓
locale resolution
   ↓
project-specific transformation
   ↓
resolved data
   ↓
Jinja
   ↓
Markdown
   ↓
HTML
```

The engine should provide a clean hook for this transformation.

The engine should not implement application-specific selection behavior itself.

This is particularly important for downstream projects such as CV generation.

---

# 20. Jinja Macros

Reusable presentation logic should use native Jinja macros.

Conventional location:

```text
templates/macros/
```

Example:

```jinja
{% macro address(person) %}
<div class="address">
<strong>{{ person.name }}</strong><br>
{{ person.street }}<br>
{{ person.city }}
</div>
{% endmacro %}
```

Usage:

```jinja
{% from "macros/address.html.j2" import address %}

{{ address(data.person) }}
```

Macros are appropriate when functionality is primarily about rendering markup.

No custom component system is required initially.

---

# 21. Python Extensions

Logic unsuitable for Jinja templates should be implemented in Python.

Conventional location:

```text
extensions/document.py
```

Minimal extension API:

```python
def setup(env):
    ...
```

Example:

```python
def format_date(value):
    ...

def setup(env):
    env.filters["format_date"] = format_date
```

Usage:

```jinja
{{ data.start_date | format_date }}
```

Initial supported Jinja extension points:

- filters
- globals
- tests

The extension mechanism should also provide a clearly separated hook for data preprocessing.

Conceptually:

```python
def transform_data(context):
    return context
```

The exact API may be refined during implementation, but presentation extensions and data transformation should remain distinct responsibilities.

---

# 22. Templates

If no outer HTML template is provided, use a built-in minimal template.

Conceptually:

```html
<!doctype html>
<html lang="{{ document.language | default('en') }}">
<head>
    <meta charset="utf-8">
    <title>{{ document.title }}</title>
</head>
<body>
    {{ content }}
</body>
</html>
```

Projects may supply:

```text
templates/default.html.j2
```

or another explicitly selected template.

The outer template defines the HTML document shell.

The source document defines its content.

---

# 23. CSS

CSS is the only initial styling and layout system.

Use it for:

- typography
- spacing
- colors
- page dimensions
- margins
- page breaks
- print rules
- running headers/footers where supported by the PDF backend

No custom styling DSL should be introduced.

---

# 24. Assets

Assets should resolve predictably relative to the project.

Example:

```markdown
![Logo](assets/logo.svg)
```

HTML:

```html
<img src="assets/logo.svg">
```

The HTML and PDF renderers must resolve project-local assets consistently.

---

# 25. Output

Required initial outputs:

```text
HTML
PDF
```

Default generated files:

```text
build/document.html
build/document.pdf
```

The output filename may derive from the entry document or configuration.

Explicit override should be possible:

```bash
ginja build document.md.j2 --output build/report.pdf
```

---

# 26. CLI

Minimum intended interface:

```bash
ginja build document.md
```

Supported options should eventually include:

```bash
ginja build document.md.j2

ginja build document.md.j2 --format html
ginja build document.md.j2 --format pdf

ginja build document.md.j2 --profile data-science
ginja build document.md.j2 --locale de

ginja build document.md.j2 \
    --profile data-science \
    --locale de

ginja build document.md.j2 --output build/custom.pdf
```

The CLI should favor sensible project conventions over large numbers of required arguments.

---

# 27. Build Matrix

Generating combinations of profiles and locales is useful but is not required for the first engine implementation.

A later generic build matrix may support:

```toml
[[builds]]
profile = "data-science"
locale = "en"

[[builds]]
profile = "data-science"
locale = "de"

[[builds]]
profile = "analytics"
locale = "en"
```

Conceptually:

```bash
ginja build-all
```

This feature should remain generic rather than CV-specific.

It may be postponed until a downstream project demonstrates the exact required behavior.

---

# 28. Pandoc

Pandoc is not a core dependency.

Core pipeline:

```text
Jinja2
   ↓
Markdown parser
   ↓
HTML
   ↓
HTML/CSS renderer
```

Pandoc may later be implemented as an optional backend.

Its potential benefits include:

- DOCX output
- EPUB output
- additional Markdown dialects
- structured AST transformations
- conversion to LaTeX or Typst
- broader interoperability

Reasons not to require it initially:

- additional dependency
- additional document model
- additional conceptual complexity
- less direct Markdown/HTML behavior
- unnecessary for HTML/PDF generation

Therefore:

```text
Core engine:       no Pandoc dependency
Future extension:  optional Pandoc backend
```

The architecture should avoid preventing future Pandoc integration.

---

# 29. Error Handling

Errors should identify:

- source file
- line where possible
- processing stage
- underlying error

Relevant stages include:

```text
configuration
TOML loading
Jinja rendering
include resolution
Markdown parsing
HTML generation
PDF rendering
Python extension loading
```

Missing includes, malformed TOML, undefined required variables, and extension failures should fail clearly rather than silently producing incomplete output.

During development, Jinja should preferably use strict undefined-variable behavior.

---

# 30. Determinism

Given:

- the same source files
- the same configuration
- the same profile
- the same locale
- the same engine version

the build should produce functionally equivalent output.

Avoid hidden environment-dependent behavior where practical.

---

# 31. Security Boundary

Python extensions execute arbitrary code and must be treated as trusted project code.

Likewise, templates should not be considered safe for rendering untrusted arbitrary Jinja input.

The engine is initially a local authoring/build tool, not a sandboxed multi-user template service.

Do not add sandbox complexity to the first implementation.

---

# 32. Explicitly Deferred Features

The following are outside the initial scope:

- custom document language
- semantic component framework
- CV-specific abstractions
- ATS-specific logic
- bibliography management
- citation processing
- mathematics
- automatic cross-references
- automatic figure numbering
- automatic section numbering
- sophisticated table-of-contents system
- schema validation
- database integration
- GUI editor
- browser application
- package registry
- plugin marketplace
- complex page-layout DSL
- custom CSS replacement
- custom Jinja replacement
- automatic translation
- DOCX
- EPUB
- Pandoc dependency
- advanced Markdown AST manipulation

These should only be added in response to concrete use cases.

---

# 33. Pre-release Implementation Plan

## 0.1 — Core rendering

Implement:

```text
.md
.html
.css
```

Pipeline:

```text
Markdown → HTML → CSS → HTML/PDF
```

Required:

- plain Markdown input
- raw HTML in Markdown
- CSS
- HTML output
- PDF output
- asset resolution
- basic CLI
- `build/` convention

Success criterion:

A one-file Markdown letter can be rendered to usable HTML and PDF.

---

## 0.2 — Jinja processing

Add:

```text
.md.j2
.html.j2
```

Support normal Jinja functionality:

- variables
- expressions
- `if`
- `for`
- `set`
- includes
- macros
- template inheritance
- filters
- tests

Establish file-processing semantics permanently.

Success criterion:

A document can use Jinja loops, conditions, includes, and HTML inside Markdown and produce deterministic HTML/PDF output.

---

## 0.3 — Project model

Add conventions for:

```text
document.toml
content/
templates/
styles/
assets/
build/
```

Implement:

- project-root discovery
- predictable include resolution
- template lookup
- configuration precedence
- TOML front matter

Success criterion:

A multi-file report can be built without explicit path configuration beyond the standard directory layout.

---

## 0.4 — Data and extensions

Add:

```text
data/
extensions/
templates/macros/
```

Implement:

- automatic TOML data loading
- explicit `data` namespace
- Jinja filters
- Jinja globals
- Jinja tests
- project Python extension loading
- data transformation hook

Success criterion:

A document can load structured data and render it with project-specific Python helpers while keeping templates simple.

---

## 0.5 — Profiles and locales

Add:

```text
profiles/
locales/
```

Implement:

```bash
--profile
--locale
```

Expose:

```text
profile
locale
```

as separate Jinja namespaces.

Allow project data transformation to use both.

Success criterion:

The same source document and canonical data can generate multiple document variants in multiple languages without duplicating the document template.

At this point the engine contains everything required to begin the separate CV project.

---

# 34. Initial Engine Completion Boundary

The rendering engine can be considered ready for its first downstream project when it supports:

```text
Markdown
HTML
Jinja2
CSS
TOML
includes
macros
multi-file documents
structured data
Python extensions
data preprocessing
profiles
locales
HTML output
PDF output
```

No CV-specific functionality should be added before this point.

---

# 35. Downstream CV Project

The CV generator is a separate project built on the engine.

Its purpose is to generate tailored CVs across dimensions such as:

```text
role/profile:
    AI consulting
    data science
    data analytics

language:
    English
    German
```

Example project:

```text
cv/
│
├── document.md.j2
├── document.toml
│
├── content/
│   ├── summary.md.j2
│   ├── experience.md.j2
│   ├── education.md.j2
│   ├── projects.md.j2
│   └── skills.md.j2
│
├── data/
│   ├── person.toml
│   ├── experience.toml
│   ├── education.toml
│   ├── projects.toml
│   └── skills.toml
│
├── profiles/
│   ├── ai-consulting.toml
│   ├── data-science.toml
│   └── data-analytics.toml
│
├── locales/
│   ├── en.toml
│   └── de.toml
│
├── templates/
│   ├── cv.html.j2
│   └── macros/
│       └── cv.html.j2
│
├── styles/
│   └── cv.css
│
├── extensions/
│   └── document.py
│
└── build/
```

---

# 36. CV Architecture

The CV project should follow:

```text
canonical CV data
      ↓
selected profile
      ↓
selected locale
      ↓
CV-specific filtering and transformation
      ↓
resolved CV data
      ↓
generic rendering engine
      ↓
HTML/PDF
```

Canonical data should remain independent of a specific generated CV.

Do not maintain separate source CVs such as:

```text
cv-data-science-en.md
cv-data-science-de.md
cv-consulting-en.md
...
```

unless exceptional content genuinely requires it.

---

# 37. CV Canonical Data

Example:

```toml
[[jobs]]
id = "example-company"
company = "Example Company"

role.en = "Senior Data Scientist"
role.de = "Senior Data Scientist"

start = "2022-01"
end = "2025-06"

tags = [
    "data-science",
    "ai-consulting",
    "python",
    "client-work"
]
```

Projects and achievements should have stable identifiers where profile-specific selection is needed.

Example:

```toml
[[projects]]
id = "forecasting-platform"

title.en = "Demand Forecasting Platform"
title.de = "Plattform zur Nachfrageprognose"

tags = [
    "data-science",
    "analytics"
]
```

---

# 38. CV Profiles

Example:

```toml
# profiles/data-science.toml

title = "Data Scientist"

include_tags = [
    "data-science",
    "machine-learning",
    "python"
]

experience = [
    "example-company",
    "research-lab"
]

projects = [
    "forecasting-platform",
    "recommendation-system"
]
```

Different profile:

```toml
# profiles/ai-consulting.toml

title = "AI Consultant"

include_tags = [
    "ai-consulting",
    "client-work",
    "strategy"
]

experience = [
    "example-company",
    "consulting-company"
]

projects = [
    "genai-strategy",
    "ml-platform"
]
```

These keys are interpreted by the CV project, not the rendering engine.

---

# 39. CV Localization

Generic terminology belongs in locale files.

Example:

```toml
# locales/de.toml

experience = "Berufserfahrung"
education = "Ausbildung"
projects = "Projekte"
skills = "Kenntnisse"
present = "heute"
```

Content requiring deliberate translation should remain explicitly localized in canonical data.

Example:

```toml
description.en = """
Designed and implemented a forecasting platform...
"""

description.de = """
Konzeption und Entwicklung einer Prognoseplattform...
"""
```

Automatic translation is not part of either project's initial scope.

---

# 40. CV Data Transformation

The CV project's Python extension should resolve profile and locale selection before rendering.

For example:

```python
def transform_data(context):
    # select relevant experience
    # select relevant projects
    # resolve localized strings
    # order sections/items
    # return simplified data for templates
    return context
```

Templates should receive mostly resolved content.

Prefer:

```jinja
{% for job in data.experience %}
...
{% endfor %}
```

over:

```jinja
{% for job in data.experience %}
    {% if profile.name in job.tags %}
        {% if locale.name == "de" %}
            ...
        {% endif %}
    {% endif %}
{% endfor %}
```

Business logic belongs in preprocessing, not scattered throughout presentation templates.

---

# 41. CV Output Matrix

Eventually the CV project should be able to produce combinations such as:

```text
build/
├── cv-ai-consulting-en.pdf
├── cv-ai-consulting-de.pdf
├── cv-data-science-en.pdf
├── cv-data-science-de.pdf
├── cv-data-analytics-en.pdf
└── cv-data-analytics-de.pdf
```

This may initially be implemented as repeated engine invocations.

A generic build-matrix feature can be added to the engine later if the CV project demonstrates that it is useful enough.

---

# 42. Final Architectural Boundary

The rendering engine provides:

```text
source processing
templating
composition
configuration
data loading
profiles
locales
extension hooks
HTML rendering
PDF rendering
```

The CV project provides:

```text
CV data model
relevance/tagging
profile definitions
content selection
content ordering
localization conventions
CV-specific preprocessing
CV templates
CV CSS
```

The engine must not absorb CV-specific concepts merely because the CV project is its first major consumer.

The intended dependency direction is:

```text
CV project
    ↓
document engine
```

never:

```text
document engine
    ↓
CV-specific behavior
```