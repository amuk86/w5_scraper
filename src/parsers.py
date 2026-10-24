"""Pure HTML -> data functions. No network here, so they are easy to test with fixtures."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_catalogue(html: str, page_url: str):
    """Return (absolute book URLs on this page, absolute URL of the 'next' page or None)."""
    soup = BeautifulSoup(html, "html.parser")
    # urljoin resolves relative links like "../book/index.html" - never glue strings together.
    links = [urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a[href]")]
    nxt = soup.select_one("li.next a[href]")
    return links, (urljoin(page_url, nxt["href"]) if nxt else None)


def dedupe(urls):
    """Remove duplicates but keep the original order."""
    return list(dict.fromkeys(urls))


class ParseError(Exception):
    """The page does not look like a product page at all (structure changed or wrong page)."""


def clean_text(text):
    """Collapse runs of whitespace/newlines; return None for empty."""
    if text is None:
        return None
    text = " ".join(text.split())
    return text or None


def parse_book(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Return the eight RAW fields. Missing optional values are None - never invented text."""
    soup = BeautifulSoup(html, "html.parser")
    # Aim at the product area, not the whole document: the page also has a second price
    # in the info table, and "the first thing that looks like a price" would betray us.
    product = soup.select_one("article.product_page")
    if product is None:
        raise ParseError("no <article class='product_page'> found")
    main = product.select_one(".product_main") or product

    def text_of(node):
        return clean_text(node.get_text(" ")) if node else None

    rating_node = main.select_one("p.star-rating")
    rating_text = None
    if rating_node:
        extra = [c for c in rating_node.get("class", []) if c != "star-rating"]
        rating_text = extra[0] if extra else None

    description = None
    marker = product.select_one("#product_description")
    if marker:
        description = text_of(marker.find_next_sibling("p"))

    return {
        "title": text_of(main.select_one("h1")),
        "product_url": product_url,
        "price_text": text_of(main.select_one("p.price_color")),
        "availability_text": text_of(main.select_one("p.availability")),
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
