"""The project model: entry discovery, TOML and YAML loading, configuration precedence and
the rendering context (`document`, `profile`, `locale`, the data namespace and `build`)."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml
from yaml.nodes import MappingNode

from .errors import DocumentError

# Tried in this order when the entry argument is a directory.
ENTRY_NAMES = ("document.md.j2", "document.md", "document.html.j2", "document.html")
KINDS = (".md.j2", ".md", ".html.j2", ".html")

# Built-in defaults: the bottom of the configuration precedence chain. `title` and `output`
# default to the entry's stem and are added per project. `data` names the folder of data
# files and their namespace in templates: `data = "facts"` loads facts/*.{toml,yaml,yml}
# as `facts.*`.
DEFAULTS = {"language": "en", "template": "default", "data": "data"}

# Project files may be written in either format. New files use `.yaml`; `.yml` is accepted.
STRUCTURED_SUFFIXES = (".toml", ".yaml", ".yml")

# Names a data namespace cannot take: the other context names and the outer template's.
RESERVED_NAMES = {"document", "profile", "locale", "build", "content", "styles"}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

TOML_FRONT_MATTER = re.compile(
    r"\A\+\+\+[ \t]*\r?\n(.*?)^\+\+\+[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE
)
YAML_FRONT_MATTER = re.compile(
    r"\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE
)
TOML_LINE = re.compile(r"at line (\d+)")

# PyYAML follows YAML 1.1: `yes`/`no`/`on`/`off` are booleans and `2024-01-01` is a date.
# Document values are mostly strings, so only `true`/`false` are booleans and dates stay text.
_BOOL_TAG = "tag:yaml.org,2002:bool"
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_BOOL_PATTERN = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")


def _document_resolvers() -> dict:
    resolvers = {}
    for first, entries in yaml.SafeLoader.yaml_implicit_resolvers.items():
        kept = []
        for tag, pattern in entries:
            if tag == _TIMESTAMP_TAG:
                continue
            if tag == _BOOL_TAG:
                pattern = _BOOL_PATTERN
            kept.append((tag, pattern))
        if kept:
            resolvers[first] = kept
    return resolvers


class _DocumentLoader(yaml.SafeLoader):
    """Safe YAML loader with string keys and TOML-like scalars and duplicate keys."""

    yaml_implicit_resolvers = _document_resolvers()

    def construct_mapping(self, node, deep=False):
        if isinstance(node, MappingNode):
            self.flatten_mapping(node)
        if not isinstance(node, MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, f"expected a mapping node, but found {node.id}", node.start_mark
            )
        mapping = {}
        for key_node, value_node in node.value:
            key = _string_key(self.construct_object(key_node, deep=deep), key_node)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _string_key(key, key_node):
    """YAML keys become strings, matching TOML. A boolean key becomes true or false."""

    if isinstance(key, str):
        return key
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, int):
        return str(key)
    if isinstance(key, float):
        return str(key)
    raise yaml.constructor.ConstructorError(
        "while constructing a mapping",
        key_node.start_mark,
        f"mapping key must be a string, got {type(key).__name__}",
        key_node.start_mark,
    )


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


def _yaml_error(error: yaml.YAMLError, label: str, offset: int = 0) -> DocumentError:
    mark = getattr(error, "problem_mark", None)
    line = mark.line + 1 + offset if mark is not None and mark.line is not None else None
    return DocumentError("YAML loading", str(error), label, line)


def _load_yaml(text: str, label: str, offset: int = 0) -> dict:
    try:
        value = yaml.load(text, Loader=_DocumentLoader)
    except yaml.YAMLError as error:
        raise _yaml_error(error, label, offset) from None
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise DocumentError("YAML loading", "the file must be a mapping", label)
    return value


def load_yaml(path: Path, label: str) -> dict:
    """Load a YAML file; `label` is the project-relative path used in error messages."""

    return _load_yaml(read_text(path), label)


def load_structured(path: Path, label: str) -> dict:
    """Load a TOML or YAML file."""

    if path.suffix.lower() == ".toml":
        return load_toml(path, label)
    return load_yaml(path, label)


def split_front_matter(text: str, label: str) -> tuple[dict, str]:
    """Split front matter from a source text.

    `+++` fences are TOML and `---` fences are YAML. The front matter is replaced by as many
    blank lines as it occupied, so line numbers in later error messages still match the file.
    """

    toml_match = TOML_FRONT_MATTER.match(text)
    if toml_match is not None:
        return _parsed_front_matter(toml_match, text, label, _load_toml_text)
    yaml_match = YAML_FRONT_MATTER.match(text)
    if yaml_match is not None:
        return _parsed_front_matter(yaml_match, text, label, _load_yaml)
    return {}, text


def _load_toml_text(text: str, label: str, offset: int = 0) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise _toml_error(error, label, offset) from None


def _parsed_front_matter(match: re.Match, text: str, label: str, load) -> tuple[dict, str]:
    values = load(match.group(1), label, offset=1)
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


def _and(items: list[str]) -> str:
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _files_named(folder: Path, name: str) -> list[Path]:
    return [
        path for suffix in STRUCTURED_SUFFIXES if (path := folder / f"{name}{suffix}").is_file()
    ]


def _structured_files(folder: Path) -> dict[str, list[Path]]:
    """Map each stem to its TOML/YAML files. Hidden names are ignored, as `*.toml` was."""

    grouped: dict[str, list[Path]] = {}
    if not folder.is_dir():
        return grouped
    for path in sorted(folder.iterdir()):
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.suffix.lower() not in STRUCTURED_SUFFIXES:
            continue
        grouped.setdefault(path.stem, []).append(path)
    return grouped


def _reject_duplicates(paths: list[Path], labels: list[str], stem: str, source: str) -> Path:
    if len(paths) == 1:
        return paths[0]
    raise DocumentError("configuration", f"{_and(labels)} define {stem!r}", source)


def document_config(root: Path) -> Path | None:
    """The `document.toml`, `document.yaml` or `document.yml` file, if the project has one."""

    matches = _files_named(root, "document")
    if len(matches) > 1:
        raise DocumentError(
            "configuration", f"{_and([path.name for path in matches])} define 'document'"
        )
    return matches[0] if matches else None


def document_config_label(root: Path) -> str:
    """Name of the document config file, or `document.toml` when the project has none."""

    path = document_config(root)
    return path.name if path else "document.toml"


def resolve_named(project: Project, folder: str, label: str, name: object) -> Path:
    """Find `profiles/<name>.toml` or `.yaml` (or the same under `locales/`)."""

    if not isinstance(name, str) or not re.fullmatch(r"[\w][\w.-]*", name):
        raise DocumentError("configuration", f"invalid {label} name {name!r}")
    directory = project.root / folder
    matches = _files_named(directory, name)
    if not matches:
        available = ", ".join(sorted(_structured_files(directory))) or "none"
        message = f"unknown {label} {name!r}; available: {available}"
        raise DocumentError("configuration", message, f"{folder}/")
    labels = [f"{folder}/{path.name}" for path in matches]
    return _reject_duplicates(matches, labels, name, f"{folder}/")


def load_named(project: Project, folder: str, label: str, name: object) -> dict:
    """Load `profiles/<name>.toml` or `.yaml`, or the same under `locales/`."""

    path = resolve_named(project, folder, label, name)
    return load_structured(path, f"{folder}/{path.name}")


def load_data(project: Project, name: str = "data") -> dict:
    """Load every `<name>/*.{toml,yaml,yml}` file as `<name>.<stem>`."""

    folder = project.root / name
    loaded = {}
    for stem, paths in _structured_files(folder).items():
        labels = [f"{name}/{path.name}" for path in paths]
        path = _reject_duplicates(paths, labels, stem, f"{name}/")
        loaded[stem] = load_structured(path, f"{name}/{path.name}")
    return loaded


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
    data = document["data"]
    if not (isinstance(data, str) and IDENTIFIER.fullmatch(data)) or data in RESERVED_NAMES:
        reserved = ", ".join(sorted(RESERVED_NAMES))
        fail(f"data must be a folder name usable in templates (not {reserved}), got {data!r}")


def load_context(
    project: Project,
    *,
    profile: str | None = None,
    locale: str | None = None,
    overrides: dict | None = None,
) -> dict:
    """Assemble the Jinja context.

    `document` follows the precedence chain: built-in defaults < document.toml or
    document.yaml < the profile's `[document]` table < front matter < overrides (`--set`,
    `--profile`, `--locale`). `profile`, `locale` and the data namespace (`data`, or the name
    `document.data` sets) stay separate.
    """

    overrides = dict(overrides or {})
    if profile is not None:
        overrides["profile"] = profile
    if locale is not None:
        overrides["locale"] = locale

    config_path = document_config(project.root)
    config_label = document_config_label(project.root)
    config = load_structured(config_path, config_label) if config_path is not None else {}
    front_matter, _ = split_front_matter(read_text(project.entry), project.entry.name)

    # The profile is chosen before its own [document] table can apply.
    profile_name = merge(config, front_matter, overrides).get("profile")
    profile_values: dict = {}
    profile_document: dict = {}
    if profile_name is not None:
        profile_path = resolve_named(project, "profiles", "profile", profile_name)
        source = f"profiles/{profile_path.name}"
        profile_values = load_structured(profile_path, source)
        profile_document = profile_values.pop("document", {})
        if not isinstance(profile_document, dict):
            raise DocumentError("configuration", "[document] must be a table", source)
        if "profile" in profile_document:
            raise DocumentError("configuration", "a profile cannot select a profile", source)

    defaults = {"title": project.stem, "output": project.stem, **DEFAULTS}
    document = merge(defaults, config, profile_document, front_matter, overrides)
    _check(document, config_label)

    # A profile may choose the default locale, so the locale is resolved last.
    locale_name = document.get("locale")
    locale_values = (
        {} if locale_name is None else load_named(project, "locales", "locale", locale_name)
    )

    return {
        "document": document,
        "profile": profile_values,
        "locale": locale_values,
        document["data"]: load_data(project, document["data"]),
        "build": {"entry": project.entry.name, "profile": profile_name, "locale": locale_name},
    }
