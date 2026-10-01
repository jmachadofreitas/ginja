"""CV preprocessing and presentation helpers.

All CV-specific logic lives here, not in the engine. `transform_data` resolves the selected
profile and locale into plain lists, so templates only loop over ready-made data:

    canonical data → profile selection → locale resolution → ordering → templates
"""

from jinja2 import pass_context

# This project's localization convention: a table whose keys are all language codes, such as
# `title.en = "…"` and `title.de = "…"`, holds one value per language.
LANGUAGES = {"en", "de"}


def localize(value, language: str):
    """Replace every localized table with its value for `language`, recursively."""

    if isinstance(value, dict):
        if value and set(value) <= LANGUAGES:
            if language not in value:
                raise ValueError(f"no {language!r} value in {value!r}")
            return value[language]
        return {key: localize(item, language) for key, item in value.items()}
    if isinstance(value, list):
        return [localize(item, language) for item in value]
    return value


def select(items: list[dict], ids: list[str], kind: str) -> list[dict]:
    """Pick items by id, in the profile's order."""

    by_id = {item["id"]: item for item in items}
    unknown = [item_id for item_id in ids if item_id not in by_id]
    if unknown:
        raise ValueError(f"the profile lists unknown {kind}: {', '.join(unknown)}")
    return [by_id[item_id] for item_id in ids]


def relevant(item: dict, wanted: set[str]) -> bool:
    """Untagged items always apply; tagged ones need a tag the profile includes."""

    tags = item.get("tags", [])
    return not tags or bool(wanted.intersection(tags))


def transform_data(context):
    language = context["build"]["locale"] or context["document"]["language"]
    context = localize(context, language)
    profile, data = context["profile"], context["data"]
    wanted = set(profile["include_tags"])

    jobs = select(data["experience"]["jobs"], profile["experience"], "experience")
    for job in jobs:
        job["highlights"] = [h["text"] for h in job["highlights"] if relevant(h, wanted)]
    data["experience"] = sorted(jobs, key=lambda job: job["start"], reverse=True)

    data["projects"] = select(data["projects"]["projects"], profile["projects"], "projects")

    groups = []
    for group in data["skills"]["groups"]:
        items = [item["name"] for item in group["items"] if relevant(item, wanted)]
        if items:
            groups.append({"name": group["name"], "items": items})
    data["skills"] = groups

    data["education"] = sorted(
        data["education"]["degrees"], key=lambda degree: degree["start"], reverse=True
    )
    return context


def month(value: str) -> str:
    """Format "2022-01" as "01/2022"."""

    year, _, month = value.partition("-")
    return f"{month}/{year}" if month else year


@pass_context
def period(context, item: dict) -> str:
    """Format an item's `start`/`end` as "01/2022 – 06/2025", or "… – present" when ongoing."""

    end = month(item["end"]) if "end" in item else context["locale"]["present"]
    return f"{month(item['start'])} – {end}"


def ongoing(item: dict) -> bool:
    return "end" not in item


def setup(env):
    env.filters["period"] = period
    env.tests["ongoing"] = ongoing
