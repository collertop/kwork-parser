"""Kwork parser that collects top items across configured categories."""

from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

from config import (
    API_BASE,
    DELAY_MAX_SEC,
    DELAY_MIN_SEC,
    ERROR_LOG_PATH,
    ITEMS_PER_PAGE,
    KWORK_COOKIE,
    MAX_ITEMS_PER_CATEGORY,
    MAX_PAGES,
    OUTPUT_DIR,
    RAW_DATA_PATH,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT_SEC,
    SUBCATEGORIES,
)
from models import KworkItem


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _log_error(message: str) -> None:
    _ensure_output_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def _load_existing_data(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            return raw
        _log_error(f"raw_data.json is not a list, resetting: {path}")
        return []
    except Exception as exc:  # noqa: BLE001
        _log_error(f"Failed to read {path}: {exc}")
        return []


def _append_category_data(path: Path, category_items: list[dict[str, Any]]) -> None:
    all_items = _load_existing_data(path)
    all_items.extend(category_items)
    with path.open("w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True", "yes", "Yes"):
        return True
    if value in (0, "0", "false", "False", "no", "No"):
        return False
    return None


def _extract_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        payload.get("data", {})
        .get("stateData", {})
        .get("viewData", {})
        .get("kworks", {})
        .get("posts", {})
        .get("data", [])
        or []
    )


def _parse_item(raw: dict[str, Any], subcategory: dict[str, str]) -> dict[str, Any]:
    item = KworkItem(
        subcategory=subcategory["name"],
        parent_slug=subcategory["parent"],
        category_slug=subcategory["slug"],
        id=_to_int(raw.get("id")),
        url=raw.get("url"),
        gtitle=raw.get("gtitle"),
        price=_to_float(raw.get("price")),
        days=_to_int(raw.get("days")),
        rating=_to_int(raw.get("rating")),
        userRating=_to_float(raw.get("userRating")),
        convertedUserRating=_to_float(raw.get("convertedUserRating")),
        userName=raw.get("userName"),
        sellerLevel=raw.get("sellerLevel"),
        queueCount=_to_int(raw.get("queueCount")),
        topBadge=_to_bool(raw.get("topBadge")),
        isFrom=_to_bool(raw.get("isFrom")),
    )
    return item.model_dump()


def _build_multipart_data(page: int) -> list[tuple[str, tuple[None, str]]]:
    return [
        ("page", (None, str(page))),
        ("s", (None, "groups")),
        ("sDirection", (None, "ASC")),
        ("sdisplay", (None, "table")),
    ]


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    if KWORK_COOKIE:
        session.headers.update({"Cookie": KWORK_COOKIE})
    return session


def _parse_category(session: requests.Session, subcategory: dict[str, str]) -> list[dict[str, Any]]:
    category_name = subcategory["name"]
    endpoint = f"{API_BASE}/{subcategory['parent']}/{subcategory['slug']}"
    collected: list[dict[str, Any]] = []

    for page in range(1, MAX_PAGES + 1):
        response = session.post(
            endpoint,
            files=_build_multipart_data(page),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        response.raise_for_status()

        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"API success=false for {category_name}, page {page}")

        posts = _extract_posts(payload)
        parsed = [_parse_item(raw, subcategory) for raw in posts]

        remaining = MAX_ITEMS_PER_CATEGORY - len(collected)
        if remaining <= 0:
            break
        collected.extend(parsed[:remaining])

        print(f"[{category_name}] Page {page} - collected {len(collected)} items")

        if len(posts) < ITEMS_PER_PAGE or len(collected) >= MAX_ITEMS_PER_CATEGORY:
            break

        time.sleep(random.uniform(DELAY_MIN_SEC, DELAY_MAX_SEC))

    return collected


def run_parser() -> int:
    _ensure_output_dir()

    total_collected = 0
    session = _create_session()

    for subcategory in SUBCATEGORIES:
        category_name = subcategory["name"]
        try:
            category_items = _parse_category(session, subcategory)
            _append_category_data(RAW_DATA_PATH, category_items)
            total_collected += len(category_items)
        except Exception as exc:  # noqa: BLE001
            _log_error(f"{category_name}: {exc}")
            print(f"[{category_name}] skipped due to error. See output/errors.log")
            continue

    print(f"Total items collected: {total_collected}")
    return total_collected


if __name__ == "__main__":
    run_parser()
