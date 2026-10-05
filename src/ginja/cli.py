import argparse
import logging
import os
import sys
import tomllib
from pathlib import Path

from . import __version__
from .build import BUILTIN_STYLES, FORMATS, build
from .errors import DocumentError
from .preview import preview
from .project import read_text

SAMPLE_DOCUMENT = """\
# Title

A paragraph of body text.

## Section

More text.

### Subsection

- A list item
- Another list item
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ginja", description="Build Markdown/Jinja documents.")
    parser.add_argument("--version", action="version", version=f"ginja {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="start a document with the default stylesheet")
    init.add_argument(
        "directory", nargs="?", default=".", type=Path, help="project directory (default: .)"
    )

    command = commands.add_parser("build", help="render a document to HTML and PDF")
    command.add_argument(
        "entry", nargs="?", default=".", help="entry document or project directory (default: .)"
    )
    command.add_argument(
        "--format",
        choices=(*FORMATS, "all"),
        help="output format (default: all, or the format of --output)",
    )
    _variant_options(command)
    command.add_argument("--output", "-o", type=Path, help="output file (.html or .pdf)")

    watch = commands.add_parser("preview", help="rebuild on every save and show the result")
    watch.add_argument(
        "entry", nargs="?", default=".", help="entry document or project directory (default: .)"
    )
    watch.add_argument(
        "--format",
        choices=FORMATS,
        default="html",
        help="html: serve and reload in the browser (default); pdf: open in the PDF viewer",
    )
    _variant_options(watch)
    watch.add_argument("--port", type=int, default=5500, help="html only (default: 5500)")
    watch.add_argument("--no-open", action="store_true", help="don't open a browser or PDF viewer")
    return parser


def _variant_options(command: argparse.ArgumentParser) -> None:
    """Options shared by `build` and `preview`."""

    command.add_argument("--profile", help="build variant from profiles/<PROFILE> (TOML or YAML)")
    command.add_argument("--locale", help="language values from locales/<LOCALE> (TOML or YAML)")
    command.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override a document setting; VALUE is parsed as TOML, else kept as a string",
    )


def parse_overrides(assignments: list[str]) -> dict:
    """Turn `KEY=VALUE` strings into nested overrides; dotted keys create tables."""

    overrides: dict = {}
    for assignment in assignments:
        key, separator, raw = assignment.partition("=")
        if not separator or not key.strip():
            raise DocumentError("configuration", f"--set expects KEY=VALUE, got {assignment!r}")
        try:
            value = tomllib.loads(f"value = {raw}")["value"]
        except tomllib.TOMLDecodeError:
            value = raw
        *parents, leaf = key.strip().split(".")
        table = overrides
        for part in parents:
            table = table.setdefault(part, {})
            if not isinstance(table, dict):
                raise DocumentError("configuration", f"--set {key}: {part} is not a table")
        table[leaf] = value
    return overrides


def init_project(directory: Path) -> list[Path]:
    """Write `document.md` and a copy of the built-in stylesheet. Refuse to overwrite either."""

    document = directory / "document.md"
    stylesheet = directory / "styles" / "document.css"
    conflicts = [path for path in (document, stylesheet) if path.exists()]
    if conflicts:
        listed = ", ".join(path.as_posix() for path in conflicts)
        raise DocumentError("init", f"refusing to overwrite {listed}")
    try:
        stylesheet.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise DocumentError("init", str(error), directory.as_posix()) from error
    document.write_text(SAMPLE_DOCUMENT, encoding="utf-8")
    stylesheet.write_text(read_text(BUILTIN_STYLES / "default.css"), encoding="utf-8")
    return [document, stylesheet]


def main(argv: list[str] | None = None) -> int:
    """Run `ginja` and return its exit status."""

    arguments = _parser().parse_args(argv)
    if arguments.command == "init":
        try:
            paths = init_project(arguments.directory)
        except DocumentError as error:
            print(f"ginja: error {error}", file=sys.stderr)
            return 1
        for path in paths:
            print(os.path.relpath(path))
        return 0

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("ginja: warning %(message)s"))
    logging.getLogger("ginja").addHandler(handler)

    if arguments.command == "preview":
        try:
            return preview(
                arguments.entry,
                fmt=arguments.format,
                port=arguments.port,
                open_result=not arguments.no_open,
                profile=arguments.profile,
                locale=arguments.locale,
                overrides=parse_overrides(arguments.overrides),
            )
        except DocumentError as error:
            print(f"ginja: error {error}", file=sys.stderr)
            return 1
        finally:
            logging.getLogger("ginja").removeHandler(handler)

    formats = {None: None, "all": FORMATS}.get(arguments.format, (arguments.format,))
    try:
        paths = build(
            arguments.entry,
            profile=arguments.profile,
            locale=arguments.locale,
            overrides=parse_overrides(arguments.overrides),
            formats=formats,
            output=arguments.output,
        )
    except DocumentError as error:
        print(f"ginja: error {error}", file=sys.stderr)
        return 1
    finally:
        logging.getLogger("ginja").removeHandler(handler)
    for path in paths:
        print(os.path.relpath(path))
    return 0
