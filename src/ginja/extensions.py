"""Project Python extensions.

`extensions/document.py` may define:
- `setup(env)`: register Jinja filters, globals and tests (presentation);
- `transform_data(context)`: return the context with resolved data (preprocessing).

Extensions are trusted project code: they run with the full rights of the build.
"""

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import jinja2

from .errors import DocumentError, traceback_frames

EXTENSION = "extensions/document.py"
MODULE_NAME = "document_extension"


def _failure(stage: str, error: Exception, path: Path) -> DocumentError:
    frames = traceback_frames(error, lambda filename: filename == str(path))
    line = frames[-1][1] if frames else None
    return DocumentError(stage, f"{type(error).__name__}: {error}", EXTENSION, line)


def load_extension(root: Path) -> ModuleType | None:
    """Import `extensions/document.py`, with `extensions/` importable for sibling helpers."""

    path = root / EXTENSION
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(MODULE_NAME, None)
        raise _failure("extension loading", error, path) from error
    finally:
        sys.path.remove(str(path.parent))
    return module


def apply_setup(module: ModuleType, environment: jinja2.Environment, root: Path) -> None:
    setup = getattr(module, "setup", None)
    if setup is None:
        return
    try:
        setup(environment)
    except Exception as error:
        raise _failure("extension loading", error, root / EXTENSION) from error


def apply_transform(module: ModuleType, context: dict, root: Path) -> dict:
    transform = getattr(module, "transform_data", None)
    if transform is None:
        return context
    try:
        result = transform(context)
    except DocumentError:
        raise
    except Exception as error:
        raise _failure("data transformation", error, root / EXTENSION) from error
    if not isinstance(result, Mapping):
        message = f"transform_data must return the context mapping, got {type(result).__name__}"
        raise DocumentError("data transformation", message, EXTENSION)
    return dict(result)
