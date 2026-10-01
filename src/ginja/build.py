"""The build pipeline.

source → Jinja (if .j2) → Markdown (if .md) → HTML fragment → outer template + CSS → HTML
HTML → PDF (if requested)
"""

import logging
import shutil
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import jinja2
from markupsafe import Markup

from . import markdown
from .errors import DocumentError, is_template_file, traceback_frames
from .extensions import apply_setup, apply_transform, load_extension
from .pdf import write_pdf
from .project import Project, find_project, load_context, read_text, split_front_matter
from .templating import make_environment

FORMATS = ("html", "pdf")
BUILTIN_STYLES = Path(__file__).parent / "styles"

logger = logging.getLogger("ginja")


def build(
    entry: str | Path = ".",
    *,
    profile: str | None = None,
    locale: str | None = None,
    overrides: dict | None = None,
    formats: Iterable[str] | None = None,
    output: str | Path | None = None,
) -> list[Path]:
    """Build a document and return the written files.

    `entry` is a source file or a project directory. `formats` defaults to both HTML and PDF,
    or to the format named by `output`'s suffix when `output` is given.
    """

    project = find_project(Path(entry))
    context = load_context(project, profile=profile, locale=locale, overrides=overrides)
    targets = output_paths(project, context, formats, output)
    html = render(project, context)

    if "html" in targets:
        path = targets["html"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8", newline="\n")
        copy_assets(project.root, path.parent)
    if "pdf" in targets:
        for warning in write_pdf(html, project.root, targets["pdf"]):
            logger.warning("[PDF rendering] %s", warning)
    return list(targets.values())


def output_paths(
    project: Project, context: dict, formats: Iterable[str] | None, output: str | Path | None
) -> dict[str, Path]:
    """Map each requested format to its file.

    By default: `build/<output>[-<profile>][-<locale>].<format>` in the project root.
    """

    formats = None if formats is None else tuple(formats)
    for name in formats or ():
        if name not in FORMATS:
            raise DocumentError("configuration", f"unknown format {name!r}; expected html or pdf")
    if output is not None:
        path = Path(output)
        name = path.suffix.lstrip(".").lower()
        if name not in FORMATS:
            raise DocumentError(
                "configuration", f"cannot infer the format of {path}; use .html or .pdf"
            )
        if formats is not None and formats != (name,):
            raise DocumentError(
                "configuration", f"output {path} does not match format {', '.join(formats)}"
            )
        return {name: path}
    selection = context["build"]
    stem = "-".join(
        filter(None, [context["document"]["output"], selection["profile"], selection["locale"]])
    )
    return {name: project.root / "build" / f"{stem}.{name}" for name in formats or FORMATS}


def render(project: Project, context: dict) -> str:
    """Render the entry document to a complete HTML document."""

    environment = make_environment(project.root, project.entry.name)
    module = load_extension(project.root)
    if module is not None:
        apply_setup(module, environment, project.root)
        context = apply_transform(module, context, project.root)

    if project.kind.endswith(".j2"):
        with jinja_errors(project):
            source = environment.get_template(project.entry.name).render(context)
    else:
        _, source = split_front_matter(read_text(project.entry), project.entry.name)

    if project.kind.startswith(".md"):
        try:
            fragment = markdown.render(source)
        except Exception as error:
            raise DocumentError(
                "Markdown parsing", f"{type(error).__name__}: {error}", project.entry.name
            ) from error
    else:
        fragment = source
    return wrap(project, environment, context, fragment)


def wrap(project: Project, environment: jinja2.Environment, context: dict, fragment: str) -> str:
    """Place the fragment in the outer HTML template, with the stylesheets inlined.

    The template receives the fragment as `content` and the CSS as `styles`. Both are passed
    as values, so Jinja never evaluates generated HTML.
    """

    document = context["document"]
    name = document["template"]
    if name is False:
        return fragment
    if not name.endswith(".j2"):
        name += ".html.j2"
    styles = [Markup(read_text(path)) for path in stylesheets(project, document)]
    with jinja_errors(project):
        try:
            template = environment.get_template(name)
        except jinja2.TemplateNotFound:
            message = f"template {name!r} not found in templates/ or the built-in templates"
            raise DocumentError("configuration", message, "document.toml") from None
        return template.render(context, content=Markup(fragment), styles=styles)


def stylesheets(project: Project, document: dict) -> list[Path]:
    """Resolve `document.style` (a name or a list), or find the conventional stylesheet.

    Names resolve in `styles/`, then the project root, then the built-in styles. Without a
    `style` setting, `styles/<stem>.css` or `<stem>.css` is used, else the built-in default.
    """

    style = document.get("style")
    if style is None:
        candidates = [
            project.root / "styles" / f"{project.stem}.css",
            project.root / f"{project.stem}.css",
        ]
        return [
            next((path for path in candidates if path.is_file()), BUILTIN_STYLES / "default.css")
        ]
    paths = []
    for name in [style] if isinstance(style, str) else style:
        candidates = [project.root / "styles" / name, project.root / name, BUILTIN_STYLES / name]
        path = next((path for path in candidates if path.is_file()), None)
        if path is None:
            message = (
                f"stylesheet {name!r} not found in styles/, the project root or the built-in styles"
            )
            raise DocumentError("configuration", message, "document.toml")
        paths.append(path)
    return paths


def copy_assets(root: Path, directory: Path) -> None:
    """Copy `assets/` next to the HTML file, so root-relative URLs work as they do in the PDF."""

    source = root / "assets"
    if source.is_dir() and directory.resolve() != root:
        shutil.copytree(source, directory / "assets", dirs_exist_ok=True)


def template_error(project: Project, stage: str, message: str, error: Exception) -> DocumentError:
    """Locate an error at its deepest template line, listing the including templates after it.

    For example, an undefined value passed to a macro fails inside the macro, while the
    mistake is usually at the call site, which then appears under "via".
    """

    frames = [
        (project.relative(path), line) for path, line in traceback_frames(error, is_template_file)
    ]
    if not frames:
        return DocumentError(stage, message)
    *callers, (path, line) = frames
    if callers:
        message += " (via " + ", ".join(f"{p}:{n}" for p, n in reversed(callers)) + ")"
    return DocumentError(stage, message, path, line)


@contextmanager
def jinja_errors(project: Project) -> Iterator[None]:
    """Translate Jinja exceptions into DocumentErrors that name the template file and line."""

    try:
        yield
    except DocumentError:
        raise
    except jinja2.TemplateSyntaxError as error:
        path = project.relative(error.filename) or error.name
        raise DocumentError(
            "Jinja rendering", f"syntax error: {error.message}", path, error.lineno
        ) from None
    except jinja2.TemplateNotFound as error:
        names = ", ".join(str(name) for name in error.templates)
        message = f"cannot find {names} in the project root, templates/ or the built-in templates"
        raise template_error(project, "include resolution", message, error) from None
    except jinja2.UndefinedError as error:
        raise template_error(project, "Jinja rendering", f"undefined: {error}", error) from None
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        raise template_error(project, "Jinja rendering", message, error) from error
