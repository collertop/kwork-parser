"""Create an Excel analytics report from parsed Kwork raw JSON data."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from config import EXCEL_PATH, OUTPUT_DIR, RAW_DATA_PATH

STOP_WORDS = {
    "и",
    "в",
    "на",
    "с",
    "по",
    "для",
    "от",
    "за",
    "к",
    "или",
    "не",
    "что",
    "это",
}

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

NUMERIC_COLUMNS = ["price", "days", "rating", "queueCount", "convertedUserRating", "userRating"]
BOOL_COLUMNS = ["topBadge", "isFrom"]

SELLER_LEVEL_MAP = {
    "новичок": 1,
    "начинающий": 1,
    "продвинутый": 2,
    "проверенный": 2,
    "профессионал": 3,
    "pro": 3,
    "топ": 4,
    "топ-продавец": 4,
    "топ продавец": 4,
}


def _load_raw_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(f"Expected JSON list in {path}")

    df = pd.DataFrame(raw)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "subcategory",
                "id",
                "url",
                "gtitle",
                "price",
                "days",
                "rating",
                "userRating",
                "convertedUserRating",
                "userName",
                "sellerLevel",
                "queueCount",
                "topBadge",
                "isFrom",
            ]
        )
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "subcategory" not in out.columns:
        out["subcategory"] = "UNKNOWN"
    out["subcategory"] = out["subcategory"].astype("string").fillna("UNKNOWN")

    for col in NUMERIC_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in BOOL_COLUMNS:
        if col in out.columns:
            out[col] = out[col].astype("boolean")

    seller_level = out.get("sellerLevel", pd.Series([None] * len(out), index=out.index))
    out["sellerLevel_num"] = (
        seller_level.astype("string").str.lower().map(SELLER_LEVEL_MAP).astype("float")
    )

    out["queue_has_items"] = out.get("queueCount", 0).fillna(0).gt(0)
    return out


def _extract_words(texts: pd.Series, top_n: int = 20) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts.dropna().astype(str):
        words = [w.lower() for w in WORD_RE.findall(text)]
        filtered = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
        counter.update(filtered)
    return counter.most_common(top_n)


def _sheet_by_subcategory(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("subcategory", dropna=False)
    stats = grouped.agg(
        items=("subcategory", "size"),
        median_price=("price", "median"),
        mean_price=("price", "mean"),
        median_rating_count=("rating", "median"),
        mean_rating_count=("rating", "mean"),
        median_days=("days", "median"),
        pct_top_badge=("topBadge", "mean"),
        pct_queue_gt_0=("queue_has_items", "mean"),
    )

    stats[["pct_top_badge", "pct_queue_gt_0"]] = (
        stats[["pct_top_badge", "pct_queue_gt_0"]] * 100
    ).round(2)
    return stats.reset_index().sort_values("subcategory")


def _sheet_top_patterns(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    top10 = (
        df.sort_values(["subcategory", "rating"], ascending=[True, False], na_position="last")
        .groupby("subcategory", dropna=False)
        .head(10)
        .copy()
    )

    top10_summary = (
        top10.groupby("subcategory", dropna=False)
        .agg(
            top10_items=("subcategory", "size"),
            avg_price_top10=("price", "mean"),
            avg_days_top10=("days", "mean"),
            avg_rating_count_top10=("rating", "mean"),
        )
        .reset_index()
        .sort_values("subcategory")
    )

    word_rows: list[dict[str, Any]] = []
    for subcategory, group in top10.groupby("subcategory", dropna=False):
        words = _extract_words(group.get("gtitle", pd.Series(dtype="string")), top_n=20)
        for rank, (word, count) in enumerate(words, start=1):
            word_rows.append(
                {
                    "subcategory": subcategory,
                    "rank": rank,
                    "word": word,
                    "count": count,
                }
            )
    words_df = pd.DataFrame(word_rows)
    return top10_summary, words_df


def _sheet_correlations(df: pd.DataFrame) -> pd.DataFrame:
    features = {
        "price": "price",
        "days": "days",
        "sellerLevel": "sellerLevel_num",
        "queueCount": "queueCount",
        "topBadge": "topBadge",
        "isFrom": "isFrom",
    }

    rows: list[dict[str, Any]] = []
    for label, column in features.items():
        temp = pd.DataFrame(
            {
                "rating": pd.to_numeric(df.get("rating"), errors="coerce"),
                "feature": pd.to_numeric(df.get(column), errors="coerce"),
            }
        ).dropna()

        corr = temp["rating"].corr(temp["feature"], method="pearson") if not temp.empty else None
        rows.append(
            {
                "feature": label,
                "pearson_corr_with_rating": corr,
                "non_null_pairs": int(temp.shape[0]),
            }
        )

    return pd.DataFrame(rows)


def _sheet_strategy(df: pd.DataFrame) -> pd.DataFrame:
    top10 = (
        df.sort_values(["subcategory", "rating"], ascending=[True, False], na_position="last")
        .groupby("subcategory", dropna=False)
        .head(10)
    )

    rows: list[dict[str, Any]] = []
    for subcategory, group in top10.groupby("subcategory", dropna=False):
        median_price = group["price"].median()
        recommended_price = median_price * 0.8 if pd.notna(median_price) else None

        words = [word for word, _ in _extract_words(group.get("gtitle", pd.Series(dtype="string")), 5)]
        median_days = group["days"].median()
        top_badge_ratio = group["topBadge"].mean()
        need_top_badge_focus = "yes" if pd.notna(top_badge_ratio) and float(top_badge_ratio) > 0.5 else "no"

        rows.append(
            {
                "subcategory": subcategory,
                "recommended_price": recommended_price,
                "recommended_title_words": ", ".join(words),
                "recommended_days": median_days,
                "need_top_badge_focus": need_top_badge_focus,
            }
        )

    return pd.DataFrame(rows).sort_values("subcategory")


def run_analysis(raw_path: Path = RAW_DATA_PATH, excel_path: Path = EXCEL_PATH) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = _load_raw_df(raw_path)
    df = _normalize(raw_df)

    by_subcategory = _sheet_by_subcategory(df)
    top10_summary, top_words = _sheet_top_patterns(df)
    correlations = _sheet_correlations(df)
    strategy = _sheet_strategy(df)

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="raw_data", index=False)
        by_subcategory.to_excel(writer, sheet_name="by_subcategory", index=False)

        top10_summary.to_excel(writer, sheet_name="top_patterns", index=False, startrow=0)
        start_words_row = len(top10_summary) + 3
        top_words.to_excel(writer, sheet_name="top_patterns", index=False, startrow=start_words_row)

        correlations.to_excel(writer, sheet_name="correlations", index=False)
        strategy.to_excel(writer, sheet_name="strategy", index=False)

    return excel_path


if __name__ == "__main__":
    output = run_analysis()
    print(f"Analysis file created: {output}")
