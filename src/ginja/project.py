"""The project model: entry discovery, TOML loading, configuration precedence and the
rendering context (`document`, `profile`, `locale`, `data` and `build`)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import DocumentError

# Tried in this order when the entry argument is a directory.
ENTRY_NAMES = ("document.md.j2", "document.md", "document.html.j2", "document.html")
KINDS = (".md.j2", ".md", ".html.j2", ".html")

# Built-in defaults: the bottom of the configuration precedence chain. `title` and `output`
# default to the entry's stem and are added per project.
DEFAULTS = {"language": "en", "template": "default"}

FRONT_MATTER = re.compile(
    r"\A\+\+\+[ \t]*\r?\n(.*?)^\+\+\+[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE
)
TOML_LINE = re.compile(r"at line (\d+)")


@dataclass
class Project:
    root: Path
    entry: Path
    kind: str  # one of KINDS
    stem: str  # the entry name without its processing suffixes: "document" for document.md.j2

    def relative(self, path: str | Path | None) -> str | None:
        """Show a path relative to the project root, so messages don't depend on the checkout."""

        if path is None:
            return None
        try:
            return Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return Path(path).name


def find_project(path: Path) -> Project:
    """Resolve the entry document; the project root is the directory that contains it."""

    path = path.resolve()
    if path.is_dir():
        found = next((path / name for name in ENTRY_NAMES if (path / name).is_file()), None)
        if found is None:
            expected = ", ".join(ENTRY_NAMES)
            raise DocumentError(
                "configuration", f"no entry document; expected {expected}", str(path)
            )
        path = found
    if not path.is_file():
        raise DocumentError("configuration", "entry document not found", str(path))
    kind = next((kind for kind in KINDS if path.name.endswith(kind)), None)
    if kind is None:
        expected = ", ".join(f"*{kind}" for kind in KINDS)
        raise DocumentError(
            "configuration", f"unsupported entry type; expected {expected}", str(path)
        )
    return Project(root=path.parent, entry=path, kind=kind, stem=path.name[: -len(kind)])


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _toml_error(error: tomllib.TOMLDecodeError, label: str, offset: int = 0) -> DocumentError:
    match = TOML_LINE.search(str(error))
    line = int(match.group(1)) + offset if match else None
    return DocumentError("TOML loading", str(error), label, line)


def load_toml(path: Path, label: str) -> dict:
    """Load a TOML file; `label` is the project-relative path used in error messages."""

    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise _toml_error(error, label) from None


def split_front_matter(text: str, label: str) -> tuple[dict, str]:
    """Split TOML front matter (`+++` fences) from a source text.

    The front matter is replaced by as many blank lines as it occupied, so line numbers in
    later error messages still match the file.
    """

    match = FRONT_MATTER.match(text)
    if match is None:
        return {}, text
    try:
        values = tomllib.loads(match.group(1))
    except tomllib.TOMLDecodeError as error:
        raise _toml_error(error, label, offset=1) from None
    return values, "\n" * match.group(0).count("\n") + text[match.end() :]


def merge(*layers: dict) -> dict:
    """Merge configuration layers, later ones winning; tables merge key by key."""

    merged: dict = {}
    for layer in layers:
        for key, value in layer.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merge(merged[key], value)
            else:
                merged[key] = value
    return merged


def load_named(project: Project, folder: str, label: str, name: object) -> dict:
    """Load `profiles/<name>.toml` or `locales/<name>.toml`."""

    if not isinstance(name, str) or not re.fullmatch(r"[\w][\w.-]*", name):
        raise DocumentError("configuration", f"invalid {label} name {name!r}")
    path = project.root / folder / f"{name}.toml"
    if not path.is_file():
        available = ", ".join(sorted(p.stem for p in (project.root / folder).glob("*.toml")))
        message = f"unknown {label} {name!r}; available: {available or 'none'}"
        raise DocumentError("configuration", message, f"{folder}/")
    return load_toml(path, f"{folder}/{name}.toml")


def load_data(project: Project) -> dict:
    """Load every `data/*.toml` file as `data.<stem>`."""

    folder = project.root / "data"
    return {
        path.stem: load_toml(path, f"data/{path.name}") for path in sorted(folder.glob("*.toml"))
    }


def _check(document: dict, source: str) -> None:
    def fail(message: str) -> None:
        raise DocumentError("configuration", message, source)

    template = document["template"]
    if template is not False and not (isinstance(template, str) and template):
        fail(f"template must be a template name or false, got {template!r}")
    style = document.get("style")
    if style is not None:
        names = [style] if isinstance(style, str) else style
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            fail(f"style must be a stylesheet name or a list of names, got {style!r}")
    if not (isinstance(document["output"], str) and document["output"]):
        fail(f"output must be a non-empty file name, got {document['output']!r}")


def load_context(
    project: Project,
    *,
    profile: str | None = None,
    locale: str | None = None,
    overrides: dict | None = None,
) -> dict:
    """Assemble the Jinja context.

    `document` follows the precedence chain: built-in defaults < document.toml < the profile's
    `[document]` table < front matter < overrides (`--set`, `--profile`, `--locale`).
    `profile`, `locale` and `data` stay separate namespaces.
    """

    overrides = dict(overrides or {})
    if profile is not None:
        overrides["profile"] = profile
    if locale is not None:
        overrides["locale"] = locale

    config_path = project.root / "document.toml"
    config = load_toml(config_path, "document.toml") if config_path.is_file() else {}
    front_matter, _ = split_front_matter(read_text(project.entry), project.entry.name)

    # The profile is chosen before its own [document] table can apply.
    profile_name = merge(config, front_matter, overrides).get("profile")
    profile_values: dict = {}
    profile_document: dict = {}
    if profile_name is not None:
        profile_values = load_named(project, "profiles", "profile", profile_name)
        profile_document = profile_values.pop("document", {})
        source = f"profiles/{profile_name}.toml"
        if not isinstance(profile_document, dict):
            raise DocumentError("configuration", "[document] must be a table", source)
        if "profile" in profile_document:
            raise DocumentError("configuration", "a profile cannot select a profile", source)

    defaults = {"title": project.stem, "output": project.stem, **DEFAULTS}
    document = merge(defaults, config, profile_document, front_matter, overrides)
    _check(document, "document.toml")

    # A profile may choose the default locale, so the locale is resolved last.
    locale_name = document.get("locale")
    locale_values = (
        {} if locale_name is None else load_named(project, "locales", "locale", locale_name)
    )

    return {
        "document": document,
        "profile": profile_values,
        "locale": locale_values,
        "data": load_data(project),
        "build": {"entry": project.entry.name, "profile": profile_name, "locale": locale_name},
    }
