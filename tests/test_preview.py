import threading
from urllib.request import urlopen

from ginja import build, preview


def test_snapshot_skips_build_and_hidden_directories(make_project):
    root = make_project(
        {
            "document.md": "# A\n",
            "content/part.md": "B\n",
            "build/document.html": "<p>old</p>\n",
            ".git/config": "x\n",
            "extensions/__pycache__/document.pyc": "x\n",
        }
    )
    files = {path.relative_to(root).as_posix() for path in preview.snapshot(root)}
    assert files == {"document.md", "content/part.md"}


def test_inject_reload_goes_before_body_end():
    page = preview.inject_reload("<html><body><p>x</p></body></html>")
    assert page.index(preview.RELOAD_SCRIPT) < page.index("</body>")
    assert preview.inject_reload("<p>fragment</p>").endswith(preview.RELOAD_SCRIPT)


def test_rebuild_returns_the_error_instead_of_raising(make_project, capsys):
    root = make_project({"document.md.j2": "{{ data.broken }}\n", "data/broken.toml": "x = \n"})
    paths, message = preview.rebuild(root, fmt="html")
    assert paths == []
    assert "[TOML loading] data/broken.toml:1" in message
    assert "✗ ginja: error" in capsys.readouterr().err


def test_server_serves_the_page_with_reload_and_the_error(make_project):
    root = make_project({"document.md": "# Hello\n"})
    (page,) = build(root, formats=["html"])
    state = {"version": 3, "error": None, "page": page}
    server = preview.make_server(root / "build", state, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        html = urlopen(f"{base}/").read().decode()
        assert "<h1>Hello</h1>" in html
        assert preview.RELOAD_SCRIPT in html
        assert urlopen(f"{base}{preview.VERSION_PATH}").read() == b"3"
        state["error"] = "ginja: error <broken>"
        html = urlopen(f"{base}/").read().decode()
        assert "&lt;broken&gt;" in html
        assert preview.RELOAD_SCRIPT in html
    finally:
        server.shutdown()
        server.server_close()
