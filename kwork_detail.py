import re
import html as html_module
import time
import logging
import os
import requests

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

        match = re.search(
            r'window\.stateData\s*=\s*(\{.+?\});\s*window\.',
            resp.text, re.DOTALL
        )
        if not match:
            logger.warning(f"stateData не найден: {full_url}")
            return EMPTY.copy()

        import json
        state = json.loads(match.group(1))
        kwork = state.get("kwork", {})
        result = {}

        # Описание — декодируем HTML entities, убираем теги
        gdesc = kwork.get("gdesc_source", "") or kwork.get("gdesc", "") or ""
        gdesc = html_module.unescape(gdesc)
        clean_desc = re.sub(r'<[^>]+>', '', gdesc).strip()
        result["description_length"] = len(clean_desc)

        # Заголовок
        gtitle = kwork.get("gtitle", "") or ""
        result["title_length"] = len(gtitle)

        # Видео
        result["has_video"] = bool(
            re.search(r'youtube|vimeo|<video', resp.text, re.I)
        )

        # Изображения
        first_pic = state.get("firstPicture", {}) or {}
        result["images_count"] = 1 if first_pic.get("src") else 0

        # Портфолио кворка (не продавца)
        kwork_portfolio = state.get("kworkPortfolio", []) or []
        result["has_portfolio"] = len(kwork_portfolio) > 0
        result["portfolio_count"] = len(kwork_portfolio)

        # FAQ
        faq = state.get("kworkFaq", []) or []
        result["has_faq"] = len(faq) > 0

        # Тарифы
        packages = kwork.get("packages", []) or []
        is_package = kwork.get("isPackage", False)
        result["has_tiers"] = bool(is_package and len(packages) > 0)
        result["price_standard"] = None
        result["price_premium"] = None
        if packages:
            prices = sorted(
                [p.get("price", 0) for p in packages if isinstance(p, dict) and p.get("price")]
            )
            if len(prices) >= 1:
                result["price_standard"] = float(prices[0])
            if len(prices) >= 2:
                result["price_premium"] = float(prices[-1])

        # Срок из kwork.days
        days = kwork.get("days")
        try:
            result["delivery_days_base"] = int(days) if days is not None else None
        except (ValueError, TypeError):
            result["delivery_days_base"] = None

        # Теги из classifications
        tags = []
        for cl in kwork.get("classifications", []) or []:
            if not isinstance(cl, dict):
                continue
            for child in cl.get("children", []) or []:
                if not isinstance(child, dict):
                    continue
                if child.get("title"):
                    tags.append(child["title"])
        result["tags"] = tags

        # Повторные заказы — недоступно через stateData
        result["repeat_orders_pct"] = None

        return result

    except Exception as e:
        logger.error(f"Ошибка при парсинге {full_url}: {e}")
        return EMPTY.copy()
