"""Bangladesh Division → Zila → Thana lookup for admission addresses."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "bd_geo.json"


@lru_cache(maxsize=1)
def tree() -> dict[str, dict[str, list[str]]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def divisions() -> list[str]:
    return sorted(tree())


def zilas(division: str) -> list[str]:
    return sorted(tree().get(division or "", {}))


def thanas(division: str, zila: str) -> list[str]:
    return list(tree().get(division or "", {}).get(zila or "", []))


def all_zilas() -> list[str]:
    names: set[str] = set()
    for districts in tree().values():
        names.update(districts)
    return sorted(names)


def all_thanas() -> list[str]:
    names: set[str] = set()
    for districts in tree().values():
        for upazilas in districts.values():
            names.update(upazilas)
    return sorted(names)


def is_valid(division: str, zila: str, thana: str) -> bool:
    return thana in tree().get(division or "", {}).get(zila or "", [])


def compose(division: str = "", zila: str = "", thana: str = "", line: str = "") -> str:
    parts = [p.strip() for p in (line, thana, zila, division) if p and str(p).strip()]
    return ", ".join(parts)
