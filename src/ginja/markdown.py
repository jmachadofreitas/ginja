"""The engine's one Markdown implementation.

markdown-it-py with the CommonMark preset, raw HTML passed through, and GFM-style tables,
strikethrough and footnotes added. Each heading opens a section whose id comes from the
heading text, or from a pandoc-style `{#id}` at the end of the heading, so a stylesheet can
target that section.
"""

import re

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin

# A pandoc-style identifier at the end of a heading: `## Publications {#publications}`.
# Pandoc also accepts spaces inside the braces; Jinja templates need them, because `{#`
# starts a Jinja comment: `## {{ locale.publications }} { #publications }`.
EXPLICIT_ID = re.compile(r"\s*\{\s*#([A-Za-z][\w.:-]*)\s*\}\s*$")


def _slug(title: str) -> str:
    """Pandoc-style identifier: lowercase, spaces to hyphens, no leading number."""

    text = title.strip().lower()
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-.")
    while text and not text[0].isalpha():
        text = text[1:].lstrip("-.")
    return text or "section"


def _unique(slug: str, seen: set[str]) -> str:
    candidate = slug
    number = 1
    while candidate in seen:
        candidate = f"{slug}-{number}"
        number += 1
    seen.add(candidate)
    return candidate


def _heading_text(token: Token) -> str:
    parts: list[str] = []

    def walk(node: Token) -> None:
        if node.type in ("text", "code_inline"):
            parts.append(node.content)
        for child in node.children or []:
            walk(child)

    walk(token)
    return "".join(parts)


def _take_explicit_id(inline: Token) -> str | None:
    """Remove a trailing `{#id}` from a heading's inline token and return the id."""

    children = inline.children or []
    start = len(children)
    while start and children[start - 1].type == "text":
        start -= 1
    match = EXPLICIT_ID.search("".join(child.content for child in children[start:]))
    if match is None:
        return None
    keep = match.start()
    for child in children[start:]:
        child.content, keep = child.content[:keep], max(0, keep - len(child.content))
    inline.content = EXPLICIT_ID.sub("", inline.content)
    return match.group(1)


def _html(content: str) -> Token:
    return Token("html_block", "", 0, content=content)


def _section_ids(state: StateCore) -> None:
    """Wrap each heading and the blocks that follow it in `<section id="...">`.

    A heading closes any open section of the same or higher level. A lower heading stays
    inside the higher one. The id is the heading's `{#id}` if it ends with one, else a slug
    of its text that avoids every id already taken. The id is not repeated on the heading.
    """

    tokens = state.tokens
    inlines = {
        index: tokens[index + 1]
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
        and index + 1 < len(tokens)
        and tokens[index + 1].type == "inline"
    }
    # Explicit ids first, so that a slug never takes an id written further down.
    explicit = {index: _take_explicit_id(inline) for index, inline in inlines.items()}
    seen = {section_id for section_id in explicit.values() if section_id}

    output: list[Token] = []
    stack: list[int] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1])
            while stack and stack[-1] >= level:
                output.append(_html("</section>\n"))
                stack.pop()
            section_id = explicit.get(index)
            if section_id is None:
                inline = inlines.get(index)
                section_id = _unique(_slug(_heading_text(inline) if inline else ""), seen)
            output.append(_html(f'<section id="{section_id}">\n'))
            stack.append(level)
        output.append(token)
    while stack:
        output.append(_html("</section>\n"))
        stack.pop()
    state.tokens = output


def _section_plugin(md: MarkdownIt) -> None:
    md.core.ruler.push("section_ids", _section_ids)


_parser = (
    MarkdownIt("commonmark", {"html": True})
    .enable(["table", "strikethrough"])
    .use(footnote_plugin)
    .use(_section_plugin)
)


def render(text: str) -> str:
    """Convert a Markdown document or block to an HTML fragment."""

    return _parser.render(text)


def render_inline(text: str) -> str:
    """Convert inline Markdown (no paragraphs or blocks) to HTML."""

    return _parser.renderInline(text)
