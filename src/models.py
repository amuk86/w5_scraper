"""The shape of a finished record, defined once. Everything is validated against it before storage."""
import re
from typing import Optional

from pydantic import BaseModel, field_validator

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
# Real data must be https. The local prefixes exist only so the offline mock site can be tested.
ALLOWED_URL_PREFIXES = ("https://", "http://127.0.0.1", "http://localhost")


def parse_price(price_text: Optional[str]) -> Optional[float]:
    """'£51.77' -> 51.77.  Also survives 'Â£51.77' (a classic encoding accident) and '£1,051.77'."""
    if not price_text:
        return None
    match = re.search(r"\d[\d,]*(?:\.\d+)?", price_text)
    return round(float(match.group().replace(",", "")), 2) if match else None


def parse_stock(availability_text: Optional[str]) -> Optional[int]:
    """'In stock (22 available)' -> 22.  No number in the text -> None."""
    match = re.search(r"\((\d+) available\)", availability_text or "")
    return int(match.group(1)) if match else None


def normalize(raw: dict) -> dict:
    """Add clean values NEXT TO the raw ones - the originals are kept for provenance."""
    clean = dict(raw)
    clean["price_gbp"] = parse_price(raw.get("price_text"))
    clean["rating"] = RATING_WORDS.get(raw.get("rating_text"))
    clean["stock_count"] = parse_stock(raw.get("availability_text"))
    return clean


class BookRecord(BaseModel):
    title: str
    product_url: str            # canonical URL = the record's identity
    price_text: str
    price_gbp: float
    availability_text: str
    stock_count: Optional[int] = None
    rating_text: str
    rating: int
    description: Optional[str] = None   # the only optional scraped field
    source_page: str
    fetched_at: str

    @field_validator("title", "price_text", "availability_text", "rating_text")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("price_gbp")
    @classmethod
    def price_not_negative(cls, v):
        if v < 0:
            raise ValueError("price must not be negative")
        return v

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("rating must be 1-5")
        return v

    @field_validator("product_url")
    @classmethod
    def url_is_absolute(cls, v):
        if not v.startswith(ALLOWED_URL_PREFIXES):
            raise ValueError("product_url must be an absolute https:// URL")
        return v


def explain(exc) -> str:
    """Turn a pydantic ValidationError into one readable line."""
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'record'}: {e['msg']}" for e in exc.errors())
