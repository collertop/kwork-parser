"""Pydantic models for Kwork parser data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KworkItem(BaseModel):
    subcategory: str | None = None
    parent_slug: str | None = None
    category_slug: str | None = None

    id: int | None = None
    url: str | None = None
    gtitle: str | None = None

    price: float | None = None
    days: int | None = None

    rating: int | None = Field(default=None, description="Review count")
    userRating: float | None = Field(default=None, description="Percentage 0-100")
    convertedUserRating: float | None = Field(default=None, description="Stars, e.g. 4.9")

    userName: str | None = None
    sellerLevel: int | None = None

    queueCount: int | None = None
    topBadge: bool | None = None
    isFrom: bool | None = None
