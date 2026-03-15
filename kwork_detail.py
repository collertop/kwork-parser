import re
import time
import logging
import os
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMPTY = {
    "description_length": None,
    "title_length": None,
    "has_video": None,
    "images_count": None,
    "has_portfolio": None,
    "portfolio_count": None,
    "has_faq": None,
    "has_tiers": None,
    "price_standard": None,
    "price_premium": None,
    "delivery_days_base": None,
    "tags": None,
    "repeat_orders_pct": None,
}

def fetch_kwork_detail(kwork_url: str, cookie: str) -> dict:
    if not kwork_url:
        return EMPTY.copy()

    full_url = f"https://kwork.ru{kwork_url}"
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(full_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"HTTP {resp.status_code} для {full_url}")
            return EMPTY.copy()

        soup = BeautifulSoup(resp.text, "html.parser")
        result = {}

        # Описание
        desc_el = soup.select_one(".kwork-description, .want-card__description")
        desc_text = desc_el.get_text(strip=True) if desc_el else ""
        result["description_length"] = len(desc_text)

        # Заголовок
        title_el = soup.select_one("h1")
        result["title_length"] = len(title_el.get_text(strip=True)) if title_el else None

        # Видео
        result["has_video"] = bool(
            soup.select_one("video, iframe[src*='youtube'], iframe[src*='vimeo']")
        )

        # Изображения
        images = soup.select("[class*='gallery'] img")
        result["images_count"] = len(images)

        # Портфолио
        portfolio = soup.select("[class*='portfolio']")
        result["has_portfolio"] = len(portfolio) > 0
        result["portfolio_count"] = len(portfolio)

        # FAQ
        result["has_faq"] = bool(soup.select_one("[class*='faq'], [class*='accordion']"))

        # Тарифы
        tiers = soup.select("[class*='package'], [class*='tier']")
        result["has_tiers"] = len(tiers) > 1
        result["price_standard"] = None
        result["price_premium"] = None

        # Срок доставки
        days_el = soup.select_one("[class*='delivery'], [class*='days']")
        if days_el:
            m = re.search(r"\d+", days_el.get_text())
            result["delivery_days_base"] = int(m.group()) if m else None
        else:
            result["delivery_days_base"] = None

        # Теги
        tags_els = soup.select("[class*='tag'] a, [class*='tags'] span")
        result["tags"] = [t.get_text(strip=True) for t in tags_els]

        # Повторные заказы
        repeat_el = soup.find(string=re.compile(r"повторн", re.I))
        if repeat_el:
            m = re.search(r"(\d+)", str(repeat_el))
            result["repeat_orders_pct"] = float(m.group(1)) if m else None
        else:
            result["repeat_orders_pct"] = None

        return result

    except Exception as e:
        logger.error(f"Ошибка при парсинге {full_url}: {e}")
        return EMPTY.copy()
