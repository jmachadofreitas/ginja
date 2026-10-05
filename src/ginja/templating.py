"""The Jinja environment: project-root template lookup, literal non-`.j2` sources, strict
undefined variables, mapping-first attribute access and the built-in `markdown` filter."""

from collections.abc import Mapping
from pathlib import Path

import jinja2
from markupsafe import Markup

from . import markdown
from .project import split_front_matter

BUILTIN_TEMPLATES = Path(__file__).parent / "templates"


class Environment(jinja2.Environment):
    """A Jinja environment where `a.b` on a mapping means `a["b"]` before any dict method.

    Without this, TOML keys such as `items`, `values` or `keys` would resolve to dict methods.
    """

    def getattr(self, obj, attribute):
        if isinstance(obj, Mapping):
            try:
                return obj[attribute]
            except (KeyError, TypeError):
                pass
        return super().getattr(obj, attribute)


class ProjectLoader(jinja2.FileSystemLoader):
    """Find templates in the project root, then `templates/`, then the built-in templates.

    Only `.j2` files are Jinja source. Any other file is literal text: each `{` is emitted
    through an expression, so the file is included verbatim and keeps its line numbers.
    Every source ends with a newline, so consecutive includes don't run together, and the
    entry document's front matter is replaced by blank lines.
    """

    def __init__(self, root: Path, entry: str | None = None) -> None:
        super().__init__([root, root / "templates", BUILTIN_TEMPLATES])
        self.entry = entry

    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        if template == self.entry:
            _, source = split_front_matter(source, template)
        if not template.endswith(".j2"):
            source = source.replace("{", "{{ '{' }}")
        if not source.endswith("\n"):
            source += "\n"
        return source, filename, uptodate


def markdown_filter(text: str, inline: bool = False) -> Markup:
    """Render a Markdown string to HTML, e.g. a description from a data file."""

    return Markup(markdown.render_inline(text) if inline else markdown.render(text))


def make_environment(root: Path, entry: str | None = None) -> Environment:
    """Create the environment for one build.

    Autoescaping is on for HTML templates and off for Markdown ones. `trim_blocks` and
    `lstrip_blocks` let block tags sit on their own lines without adding blank lines, so
    loops generate tight Markdown lists.
    """

    environment = Environment(
        loader=ProjectLoader(root, entry),
        undefined=jinja2.StrictUndefined,
        autoescape=jinja2.select_autoescape(["html", "html.j2"], default_for_string=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    environment.filters["markdown"] = markdown_filter
    return environment
