from ginja import markdown
from ginja.templating import markdown_filter


def test_commonmark_basics():
    html = markdown.render("# Title\n\nSome *emphasis* and a [link](https://example.com).\n")
    assert "<h1>Title</h1>" in html
    assert "<em>emphasis</em>" in html
    assert '<a href="https://example.com">link</a>' in html


def test_lists_images_and_fenced_code():
    html = markdown.render("- one\n- two\n\n![Logo](assets/logo.svg)\n\n```python\nx = 1\n```\n")
    assert "<ul>\n<li>one</li>\n<li>two</li>\n</ul>" in html
    assert '<img src="assets/logo.svg" alt="Logo" />' in html
    assert '<pre><code class="language-python">x = 1\n</code></pre>' in html


def test_tables():
    html = markdown.render("| a | b |\n|---|--:|\n| 1 | 2 |\n")
    assert "<table>" in html
    assert "<th>a</th>" in html
    assert '<td style="text-align:right">2</td>' in html


def test_footnotes():
    html = markdown.render("Text[^1].\n\n[^1]: The note.\n")
    assert 'class="footnote-ref"' in html
    assert "The note." in html


def test_raw_html_passes_through_unchanged():
    source = '## Contact\n\n<div class="contact">\nJane Example  \nBerlin & Co\n</div>\n'
    html = markdown.render(source)
    assert '<div class="contact">\nJane Example  \nBerlin & Co\n</div>' in html


def test_heading_section_wraps_its_list_only():
    html = markdown.render("Intro\n\n## Publications\n\n- A\n\n## Experience\n\n- B\n")
    intro, rest = html.split('<section id="publications">', 1)
    publications, experience = rest.split('<section id="experience">', 1)
    assert "<p>Intro</p>" in intro
    assert "<section" not in intro
    assert "<h2>Publications</h2>" in publications
    assert "<li>A</li>" in publications
    assert "<li>B</li>" not in publications
    assert "<li>B</li>" in experience
    assert "<h2 id=" not in html


def test_subsection_is_nested_in_its_section():
    html = markdown.render("## Section\n\n### Subsection\n\n- item\n")
    outer, inner = html.split('<section id="subsection">', 1)
    assert outer.startswith('<section id="section">')
    assert "</section>" not in outer
    assert "<li>item</li>" in inner.split("</section>", 1)[0]
    assert inner.count("</section>") == 2


def test_section_ids_drop_punctuation_and_number_duplicates():
    html = markdown.render("## Selected projects!\n\n## Selected projects!\n\n## Öffentlich\n")
    assert '<section id="selected-projects">' in html
    assert '<section id="selected-projects-1">' in html
    assert '<section id="öffentlich">' in html


def test_explicit_section_id_replaces_slug():
    html = markdown.render("## Ausgewählte Projekte {#projects}\n\n- A\n")
    assert '<section id="projects">' in html
    assert "<h2>Ausgewählte Projekte</h2>" in html
    assert "{#" not in html


def test_explicit_id_keeps_inline_markup():
    html = markdown.render("## **Bold** title {#x}\n")
    assert '<section id="x">' in html
    assert "<h2><strong>Bold</strong> title</h2>" in html


def test_explicit_id_with_spaces_for_jinja_templates():
    html = markdown.render("## Skills { #skills }\n")
    assert '<section id="skills">\n<h2>Skills</h2>' in html


def test_slug_avoids_an_explicit_id_written_later():
    html = markdown.render("## Projects\n\n## Selected work {#projects}\n")
    assert '<section id="projects-1">\n<h2>Projects</h2>' in html
    assert '<section id="projects">\n<h2>Selected work</h2>' in html


def test_markdown_filter_returns_markup():
    assert markdown_filter("**bold**") == "<p><strong>bold</strong></p>\n"
    assert markdown_filter("**bold**", inline=True) == "<strong>bold</strong>"
    assert hasattr(markdown_filter("x"), "__html__")
