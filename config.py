"""Configuration for Kwork parser project."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
RAW_DATA_PATH = OUTPUT_DIR / "raw_data.json"
EXCEL_PATH = OUTPUT_DIR / "kwork_analysis.xlsx"
ERROR_LOG_PATH = OUTPUT_DIR / "errors.log"

API_BASE = "https://kwork.ru/catalog_kworks_filters"
REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36"
    ),
}

REQUEST_TIMEOUT_SEC = 30
DELAY_MIN_SEC = 3
DELAY_MAX_SEC = 6
MAX_ITEMS_PER_CATEGORY = 50
MAX_PAGES = 3
ITEMS_PER_PAGE = 24

# Paste browser cookie header value into .env, for example:
# KWORK_COOKIE="PHPSESSID=...; c=..."
KWORK_COOKIE = os.getenv("KWORK_COOKIE", "").strip()

SUBCATEGORIES = [
    {"name": "Доработка сайтов", "parent": "website-repair", "slug": "dorabotka-sayta"},
    {"name": "Настройка сайтов", "parent": "website-repair", "slug": "nastroyka-sayta"},
    {"name": "Исправление ошибок", "parent": "website-repair", "slug": "ispravlenie-oshibok"},
    {"name": "Новый сайт", "parent": "website-development", "slug": "noviy-sayt"},
    {"name": "Копия сайта", "parent": "website-development", "slug": "kopiya-sushchestvuyushchego"},
    {"name": "Верстка по макету", "parent": "frontend", "slug": "verstka-po-dizayn-maketu"},
    {"name": "Доработка верстки", "parent": "frontend", "slug": "dorabotka-verstki"},
    {"name": "Чат-боты", "parent": "script-programming", "slug": "chat-boty"},
    {"name": "ИИ-боты", "parent": "script-programming", "slug": "ii-boty"},
    {"name": "Telegram Mini Apps", "parent": "script-programming", "slug": "telegram-mini-apps"},
    {"name": "Машинное обучение", "parent": "script-programming", "slug": "mashinnoe-obuchenie"},
]
