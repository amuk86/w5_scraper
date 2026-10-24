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
