"""The bundled examples build, and the CV variants differ as their profiles and locales say."""

import shutil
from pathlib import Path

import pytest

from ginja import DocumentError, build

EXAMPLES = Path(__file__).parents[1] / "examples"
CV = EXAMPLES / "curriculum-vitae"
PROFILES = ["ai-consulting", "data-science", "data-analytics"]
LOCALES = ["en", "de"]


def build_html(entry: Path, output: Path, **options) -> str:
    (path,) = build(entry, output=output, **options)
    return path.read_text(encoding="utf-8")


def test_letter(tmp_path):
    html = build_html(EXAMPLES / "letter" / "letter.md", tmp_path / "letter.html")
    assert "<title>Application: Data Scientist</title>" in html
    assert '<img src="assets/logo.svg"' in html
    assert (tmp_path / "assets" / "logo.svg").is_file()


def test_report(tmp_path):
    html = build_html(EXAMPLES / "report", tmp_path / "report.html")
    assert "<td>Notifications</td>" in html
    assert '<td style="text-align:right">99.12 %</td>' in html
    assert "2 service(s) missed the target:\nSearch, Notifications." in html
    assert '<div class="note">' in html  # nested include
    assert 'class="footnote-ref"' in html


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("profile", PROFILES)
def test_cv_variants_build(tmp_path, profile, locale):
    html = build_html(CV, tmp_path / "cv.html", profile=profile, locale=locale)
    assert f'<html lang="{locale}">' in html
    assert ("Berufserfahrung" in html) == (locale == "de")
    assert ("heute" in html) == (locale == "de")


def test_cv_profiles_select_projects_and_experience(tmp_path):
    consulting = build_html(CV, tmp_path / "a.html", profile="ai-consulting", locale="de")
    assert "<title>Jane Example — KI-Beraterin</title>" in consulting
    assert "Strategie für generative KI bei einem Industrieunternehmen" in consulting
    assert "Plattform zur Nachfrageprognose" not in consulting
    assert "Example Research Lab" not in consulting

    science = build_html(CV, tmp_path / "b.html", profile="data-science", locale="en")
    assert "Demand Forecasting Platform" in science
    assert "Example Research Lab" in science
    assert "Contoso Retail" not in science
    assert "PyTorch" in science and "Power BI" not in science  # skills filtered by tags


def test_cv_profile_orders_sections(tmp_path):
    analytics = build_html(CV, tmp_path / "a.html", profile="data-analytics", locale="en")
    science = build_html(CV, tmp_path / "b.html", profile="data-science", locale="en")
    assert analytics.index('id="skills"') < analytics.index('id="experience"')
    assert science.index('id="experience"') < science.index('id="skills"')


def test_cv_unknown_profile_id_fails_clearly(tmp_path):
    project = shutil.copytree(CV, tmp_path / "cv", ignore=shutil.ignore_patterns("build"))
    profile = project / "profiles" / "data-science.toml"
    profile.write_text(profile.read_text().replace('"research-lab"', '"no-such-job"'))
    with pytest.raises(DocumentError) as caught:
        build(project, formats=["html"])
    assert caught.value.stage == "data transformation"
    assert "unknown experience: no-such-job" in caught.value.message
