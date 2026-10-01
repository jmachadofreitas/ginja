"""`ginja preview`: rebuild on every save and show the result.

html: build HTML into build/ and serve it on http://127.0.0.1:PORT/. The page reloads itself
      after each rebuild, and shows the error message after a failed one.
pdf:  build the PDF into build/ and open it once in the default viewer, which reloads changed
      files (Evince, Okular and Skim do). A failed build keeps the last good PDF.

The outputs are the same files `ginja build --format html|pdf` writes. Only the standard
library is used: the watcher polls modification times, and the reload is a small script
injected into the served page, never into the file.
"""

import html
import http.server
import os
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

from .build import build
from .errors import DocumentError
from .project import find_project

VERSION_PATH = "/__doc/version"

# Polls the version and reloads the page when it changes.
RELOAD_SCRIPT = """<script>
(() => {
  let version = null;
  setInterval(async () => {
    try {
      const response = await fetch("/__doc/version", { cache: "no-store" });
      const current = await response.text();
      if (version !== null && current !== version) location.reload();
      version = current;
    } catch {}
  }, 500);
})();
</script>
"""

ERROR_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Build failed</title></head>
<body style="font: 14px/1.5 monospace; margin: 2rem; color: #9b1c1c">
<h1 style="font-size: 1.2rem">Build failed</h1>
<pre style="white-space: pre-wrap">{message}</pre>
</body></html>
"""

# Directories never watched: generated files and tool caches.
SKIPPED_DIRECTORIES = {"build", "__pycache__"}


def snapshot(root: Path) -> dict[Path, int]:
    """Modification time of every file in the project, except build/ and hidden directories."""

    files = {}
    for directory, subdirectories, names in os.walk(root):
        subdirectories[:] = [
            name
            for name in subdirectories
            if not name.startswith(".") and name not in SKIPPED_DIRECTORIES
        ]
        for name in names:
            path = Path(directory) / name
            try:
                files[path] = path.stat().st_mtime_ns
            except FileNotFoundError:  # removed while walking
                continue
    return files


def watch(root: Path, on_change: Callable[[], None], interval: float = 0.5) -> None:
    """Call `on_change` whenever a file in the project is added, removed or saved."""

    last = snapshot(root)
    while True:
        time.sleep(interval)
        current = snapshot(root)
        if current != last:
            last = current
            on_change()


def rebuild(entry: Path, *, fmt: str, **options) -> tuple[list[Path], str | None]:
    """Build one format; print the outcome and return (written files, error message)."""

    started = time.perf_counter()
    try:
        paths = build(entry, formats=[fmt], **options)
    except DocumentError as error:
        message = f"ginja: error {error}"
    except Exception as error:  # noqa: BLE001 - an extension bug must not stop the preview
        message = f"ginja: error {type(error).__name__}: {error}"
    else:
        elapsed = time.perf_counter() - started
        print(f"✓ {os.path.relpath(paths[0])} ({elapsed:.1f} s)", flush=True)
        return paths, None
    print(f"✗ {message}", file=sys.stderr, flush=True)
    return [], message


def inject_reload(page: str) -> str:
    """Insert the reload script before `</body>`, or at the end when there is none."""

    index = page.rfind("</body>")
    return page + RELOAD_SCRIPT if index == -1 else page[:index] + RELOAD_SCRIPT + page[index:]


def error_page(message: str) -> str:
    return ERROR_PAGE.format(message=html.escape(message))


def make_server(directory: Path, state: dict, port: int) -> http.server.ThreadingHTTPServer:
    """Serve `directory`. `/` is the document (`state["page"]`), or the error after a failed
    build (`state["error"]`); `/__doc/version` is `state["version"]`."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == VERSION_PATH:
                self._send(str(state["version"]), "text/plain")
            elif path == "/" or path.endswith(".html"):
                page = state.get("page")
                if path != "/":
                    page = Path(self.translate_path(path))
                if state.get("error"):
                    self._send(inject_reload(error_page(state["error"])), "text/html")
                elif page is not None and page.is_file():
                    self._send(inject_reload(page.read_text(encoding="utf-8")), "text/html")
                else:
                    self.send_error(404)
            else:
                super().do_GET()

        def _send(self, text: str, content_type: str) -> None:
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # keep the terminal for build messages
            pass

    return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)


def open_file(path: Path) -> None:
    """Open a file in the platform's default application."""

    if sys.platform == "win32":
        os.startfile(path)
        return
    command = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([command, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"Open {path} in a viewer that reloads changed files.", flush=True)


def preview(
    entry: str | Path = ".",
    *,
    fmt: str = "html",
    port: int = 5500,
    open_result: bool = True,
    **options,
) -> int:
    """Build, then rebuild on every change until Ctrl+C. `options` go to `build()`."""

    project = find_project(Path(entry))
    paths, error = rebuild(project.entry, fmt=fmt, **options)

    if fmt == "pdf":
        opened = not open_result

        def on_change() -> None:
            nonlocal opened
            written, _ = rebuild(project.entry, fmt=fmt, **options)
            if written and not opened:
                open_file(written[0])
                opened = True

        if paths and not opened:
            open_file(paths[0])
            opened = True
        print(f"Watching {os.path.relpath(project.root)} (Ctrl+C to stop)", flush=True)
        try:
            watch(project.root, on_change)
        except KeyboardInterrupt:
            pass
        return 0

    state = {"version": 0, "error": error, "page": paths[0] if paths else None}

    def on_change() -> None:
        written, message = rebuild(project.entry, fmt=fmt, **options)
        state["error"] = message
        if written:
            state["page"] = written[0]
        state["version"] += 1

    try:
        server = make_server(project.root / "build", state, port)
    except OSError as error:
        raise DocumentError("preview", f"cannot listen on port {port}: {error.strerror}") from error
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Preview: {url} (Ctrl+C to stop)", flush=True)
    if open_result:
        webbrowser.open(url)
    try:
        watch(project.root, on_change)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0
