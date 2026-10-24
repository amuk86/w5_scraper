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


def extract_all(fetcher, urls, source_page):
    """Stage 3: fetch + parse every book page. One bad page is logged and skipped."""
    raws, failures = [], []
    for url in urls:
        try:
            page = fetcher.get(url)
            raws.append(parsers.parse_book(page.html, url, source_page.get(url, "manual"), page.fetched_at))
        except FetchError as exc:
            warn(f"skipped: {exc}")
            failures.append({"url": url, "reason": exc.reason, "status": exc.status})
        except Exception as exc:                         # parse problems must not kill the run either
            warn(f"skipped (could not parse): {url}: {type(exc).__name__}: {exc}")
            failures.append({"url": url, "reason": f"{type(exc).__name__}: {exc}", "status": None})
    return raws, failures


def validate_records(raws):
    """Stage 4: normalize, validate, deduplicate by canonical URL.

    Returns (valid records, error entries, number of duplicates dropped).
    """
    from pydantic import ValidationError
    from models import BookRecord, explain, normalize

    valid, errors, seen, duplicates = [], [], set(), 0
    for raw in raws:
        clean = normalize(raw)
        try:
            record = BookRecord.model_validate(clean).model_dump()
        except ValidationError as exc:
            errors.append({"product_url": raw.get("product_url"), "reason": explain(exc), "raw": raw})
            continue
        if record["product_url"] in seen:
            duplicates += 1                                   # same book twice counts once
            continue
        seen.add(record["product_url"])
        valid.append(record)
    valid.sort(key=lambda r: r["product_url"])               # stable order -> identical reruns
    return valid, errors, duplicates


def write_json(path, data):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(base_url=config.BASE_URL, out_dir=config.OUTPUT_DIR, fetcher=None, extra_urls=()):
    """The whole pipeline. Always ends by writing run-report.json, even if pages failed."""
    import time
    from datetime import datetime, timezone
    from fetcher import PoliteFetcher

    started, t0 = datetime.now(timezone.utc), time.monotonic()
    fetcher = fetcher or PoliteFetcher()

    found = discover(fetcher, base_url.rstrip("/") + config.START_PATH)
    print(f"catalogue_pages={found.catalogue_pages}, discovered={found.discovered}, unique_urls={len(found.urls)}")

    urls = parsers.dedupe(found.urls + list(extra_urls))      # extra_urls: e.g. a deliberately fake URL
    raws, failures = extract_all(fetcher, urls, found.source_page)
    print(f"detail_pages={len(raws)}")

    valid, errors, duplicates = validate_records(raws)
    write_json(out_dir / "books.json", valid)                 # rewritten, never appended -> idempotent
    write_json(out_dir / "errors.json", errors)

    all_failures = found.failures + failures
    report = {
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round(time.monotonic() - t0, 2),
        "catalogue_pages": found.catalogue_pages,
        "urls_discovered": found.discovered,
        "unique_urls": len(found.urls),
        "pages_fetched": fetcher.network_fetches,             # real requests that succeeded
        "cache_hits": fetcher.cache_hits,
        "retries": fetcher.retries,
        "valid_records": len(valid),
        "invalid_records": len(errors),
        "duplicate_records": duplicates,
        "failed_pages": len(all_failures),
        "failures": all_failures,
    }
    write_json(out_dir / "run-report.json", report)
    print(f"valid={report['valid_records']} invalid={report['invalid_records']} "
          f"failed_pages={report['failed_pages']} duration={report['duration_seconds']}s")
    return report
