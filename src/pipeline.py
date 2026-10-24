"""The pipeline: fetch -> extract -> normalize -> validate -> store -> report."""
import sys
from dataclasses import dataclass, field

import config
import parsers
from fetcher import FetchError


def warn(msg):
    print(f"WARNING {msg}", file=sys.stderr)


@dataclass
class Discovery:
    catalogue_pages: int = 0
    discovered: int = 0                                  # links seen, duplicates included
    urls: list = field(default_factory=list)            # unique absolute book URLs
    source_page: dict = field(default_factory=dict)     # book URL -> catalogue page it was found on
    failures: list = field(default_factory=list)


def discover(fetcher, start_url, max_pages=config.MAX_CATALOGUE_PAGES) -> Discovery:
    """Stage 2: follow the site's own 'next' links, at most `max_pages` pages."""
    found, page_url = Discovery(), start_url
    all_links = []
    while page_url and found.catalogue_pages < max_pages:
        try:
            page = fetcher.get(page_url)
        except FetchError as exc:
            warn(f"catalogue page failed: {exc}")
            found.failures.append({"url": page_url, "reason": exc.reason, "status": exc.status})
            break                                         # without this page we cannot find the next
        links, nxt = parsers.parse_catalogue(page.html, page_url)
        found.catalogue_pages += 1
        for link in links:
            found.source_page.setdefault(link, page_url)
        all_links.extend(links)
        page_url = nxt
    found.discovered = len(all_links)
    found.urls = parsers.dedupe(all_links)
    return found
