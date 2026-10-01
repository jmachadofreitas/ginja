# Curriculum vitae example

One canonical data set for a fictional person, rendered as tailored CVs for 3 roles and
2 languages without duplicating any template:

```bash
just example-cv ai-consulting de       # → build/cv-ai-consulting-de.{html,pdf}
just example-cv-all                     # all six variants
```

## How it is put together

```text
canonical data (data/*.toml)
  → profile selection (profiles/<role>.toml)
  → locale resolution (field.en / field.de, locales/<code>.toml)
  → CV-specific filtering and ordering (extensions/document.py)
  → generic engine: Jinja → Markdown → HTML → PDF
```

- **`data/`** holds the canonical CV. Jobs and projects have stable `id`s. Highlights, skills
  and projects carry `tags`. Text that needs a deliberate translation is written in both
  languages, for example `role.en` and `role.de`.
- **`profiles/`** pick the jobs and projects to show, by id, and list `include_tags` to filter
  highlights and skills. `sections` sets the section order. The `[document]` table overrides
  the document title. The engine doesn't interpret any of these keys; the extension does.
- **`locales/`** hold section headings and other terms such as "present"/"heute".
- **`extensions/document.py`** does all the CV logic in `transform_data`. It resolves
  localized fields, selects and orders items, and keeps only the highlights and skills that
  match the profile's tags. Templates therefore only loop over `data.experience`,
  `data.projects`, `data.skills` and `data.education`. `setup(env)` adds a `period` filter
  and an `ongoing` test.
- **`document.md.j2`** includes `content/<section>.md.j2` for each section in the profile.
  The sections mix Markdown with the `entry_header` macro from `templates/macros/cv.html.j2`.
  Each starts with `## {{ locale.<section> }} { #<section> }` (spaces inside the braces:
  `{#` would start a Jinja comment), so the engine wraps it in
  `<section id="<section>">` whatever the language, and `styles/cv.css` can target `#skills`.
- **`templates/cv.html.j2`** is the page shell with the contact header. **`styles/cv.css`**
  holds the A4 layout.

All names and data are made up.
