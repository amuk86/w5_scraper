from pathlib import Path

import pytest
from pydantic import ValidationError

import parsers
from models import BookRecord, normalize, parse_price

FIX = Path(__file__).parent / "fixtures"
URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
SRC = "https://books.toscrape.com/catalogue/page-1.html"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_price_normalization():
    assert parse_price("£51.77") == 51.77
    assert parse_price("Â£51.77") == 51.77      # mojibake survives
    assert parse_price("£1,051.77") == 1051.77
    assert parse_price("free!") is None
    assert parse_price(None) is None


def test_relative_urls_become_absolute():
    page = "https://books.toscrape.com/catalogue/page-2.html"
    links, nxt = parsers.parse_catalogue(read("catalogue_page.html"), page)
    assert links[0] == "https://books.toscrape.com/a-light_1000/index.html"      # ../../ resolved
    assert links[1] == "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"
    assert nxt == "https://books.toscrape.com/catalogue/page-3.html"
    assert all(u.startswith("https://") for u in links)


def test_duplicate_urls_removed_in_order():
    links, _ = parsers.parse_catalogue(read("catalogue_page.html"), SRC)
    assert len(links) == 3 and len(parsers.dedupe(links)) == 2
    assert parsers.dedupe(["b", "a", "b"]) == ["b", "a"]


def test_full_book_all_eight_keys_and_whitespace_cleaned():
    raw = parsers.parse_book(read("book_with_description.html"), URL, SRC, "2026-08-06T10:00:00Z")
    assert list(raw) == ["title", "product_url", "price_text", "availability_text",
                         "rating_text", "description", "source_page", "fetched_at"]
    assert raw["title"] == "A Light in the Attic"                  # extra spaces collapsed
    assert raw["price_text"] == "£51.77"                           # NOT the £99.99 in the table
    assert raw["availability_text"] == "In stock (22 available)"
    assert raw["rating_text"] == "Three"
    clean = BookRecord.model_validate(normalize(raw))
    assert clean.price_gbp == 51.77 and clean.stock_count == 22 and clean.rating == 3


def test_missing_description_is_null_not_invented():
    raw = parsers.parse_book(read("book_no_description.html"), URL, SRC, "t")
    assert raw["description"] is None and "description" in raw
    assert raw["price_text"] == "£10.00"
    assert BookRecord.model_validate(normalize(raw)).description is None


def test_malformed_page_fails_validation_with_reason():
    raw = parsers.parse_book(read("book_malformed.html"), URL, SRC, "t")
    with pytest.raises(ValidationError) as exc:
        BookRecord.model_validate(normalize(raw))
    fields = {e["loc"][0] for e in exc.value.errors()}
    assert {"price_gbp", "rating"} <= fields


def test_non_product_page_raises_parse_error():
    with pytest.raises(parsers.ParseError):
        parsers.parse_book("<html><body>nothing here</body></html>", URL, SRC, "t")


def test_non_https_url_rejected():
    raw = parsers.parse_book(read("book_with_description.html"), "http://evil.example/x", SRC, "t")
    with pytest.raises(ValidationError):
        BookRecord.model_validate(normalize(raw))
