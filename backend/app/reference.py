import json
from functools import lru_cache

from app.config import settings


@lru_cache
def load_reference() -> dict:
    with open(settings.reference_path, "r", encoding="utf-8") as f:
        return json.load(f)


def section_keys() -> set[str]:
    return {s["key"] for s in load_reference()["sections"]}


def nav_sections() -> list[dict]:
    return sorted(
        [s for s in load_reference()["sections"] if s.get("show_in_nav")],
        key=lambda s: s["sort_order"],
    )


def category_keys() -> set[str]:
    return {c["key"] for c in load_reference()["categories"]}


def language_codes() -> set[str]:
    return {lang["code"] for lang in load_reference()["languages"]}


def default_language() -> str:
    for lang in load_reference()["languages"]:
        if lang.get("is_default"):
            return lang["code"]
    return "en"


def language_label(code: str) -> str:
    for lang in load_reference()["languages"]:
        if lang["code"] == code:
            return lang["label"]
    return code


def category_label(key: str) -> str:
    for c in load_reference()["categories"]:
        if c["key"] == key:
            return c["label"]
    return key


def status_keys() -> set[str]:
    return {s["key"] for s in load_reference()["statuses"]}


def artwork_spec(kind: str) -> dict | None:
    for s in load_reference()["artwork"]["specs"]:
        if s["kind"] == kind:
            return s
    return None


def artwork_max_bytes() -> int:
    return load_reference()["artwork"]["max_file_size_bytes"]


def artwork_allowed_mimes() -> set[str]:
    return set(load_reference()["artwork"]["allowed_mime_types"])


def artwork_tolerance() -> float:
    return load_reference()["artwork"]["aspect_ratio_tolerance"]


def required_episode_kinds() -> list[str]:
    return load_reference()["artwork"]["required_kinds_per_episode"]


def required_show_kinds() -> list[str]:
    return load_reference()["artwork"]["required_kinds_per_show"]
