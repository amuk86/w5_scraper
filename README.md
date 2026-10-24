# The polite scraper (FlyRank Internship · Backend Track · W5 · A9)

Downloads the first three catalogue pages of **Books to Scrape**, visits all 60 book pages, and turns messy HTML into clean, validated JSON — politely, without crashing on a broken page, and with an honest report at the end of every run.

Pipeline: **classify → fetch → extract → normalize → validate → store → report**

## Target classification

- **Site:** https://books.toscrape.com
- **Why:** [toscrape.com](https://toscrape.com) describes its sites as sandboxes built for people to practise scraping on. That statement is my permission.
- **How much:** the first 3 catalogue pages only (60 books), plus each book's own page (~63 requests).
- **Data collected:** title, product URL, price, availability, star rating, description (when present). No personal data.
- **robots.txt result:** _TODO — run `python src/main.py robots`, then replace this line with the status code and what it said (or "no robots file found" — a missing file is not permission, just a missing file)._
- **Why this is appropriate:** a public practice sandbox, tiny volume, I identify myself and go slowly.

I will not reuse this code on another site without checking its rules and terms first.

## Run it (Python lane, 3.10+)

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git && cd YOUR-REPO
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py          # the full run: books.json + errors.json + run-report.json
```

Before the first run, set `REPO_URL` in `src/config.py` so the user-agent points at your repo.

Stage commands (each prints its own checkpoint): `robots` · `fetch` · `discover` · `extract` · `run` (default).
Tests (no network needed): `python -m pytest -q`

Test failure handling safely — a made-up URL on *your* side, never hammering the real site:
```bash
python src/main.py run --extra-url https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html
```

Outputs: `output/books.json` (60 valid records) · `output/errors.json` (records that failed validation, with reasons) · `output/run-report.json`.

## Record schema (Pydantic, `src/models.py`)

| Field | Type | Notes |
|---|---|---|
| `title`, `price_text`, `availability_text`, `rating_text` | str, required | raw values, kept as scraped |
| `product_url` | str, required | absolute `https://` URL = canonical identity |
| `description` | str or `null` | optional — `null` when the page has none, never invented |
| `source_page`, `fetched_at` | str, required | provenance: where and when the fact came from |
| `price_gbp` | float ≥ 0 | clean number from `price_text` |
| `rating` | int 1–5 | from `rating_text` ("Three" → 3) |
| `stock_count` | int or `null` | from "In stock (22 available)" |

A record that fails goes to `errors.json` with the reason — never into `books.json`. Duplicates (same `product_url`) count once.

## Politeness rules

- **User-agent:** `FlyRankInternshipA9/1.0 (+repo link)` — an honest name and a way to reach me.
- **Delay:** at least 0.5 s between real requests (the CLI refuses a smaller `--delay`). Cache hits never wait.
- **Timeout:** 10 s per request; nothing waits forever.
- **Status check:** only `200` is parsed. Timeouts/connection errors and `5xx` get **one** retry after 2 s; `404` and `403` are never retried.
- **Cache:** every page is saved to `cache/` (git-ignored); reruns read from disk, so the site feels each page once.
- **Isolation:** one bad page is logged and skipped; the run always finishes and writes its report.

## Run report (real run)

_TODO — after your first real run, paste the contents of `output/run-report.json` here._

## Why no browser?

The data is already in the HTML the server sends, so a browser would only add cost.

## Ethics note

_(Reword this in your own words before submitting.)_ If a site offers an official API, I use that instead of scraping. I never bypass logins, paywalls, or blocks, and a `403` means stop. I collect only the fields I need and keep the volume small enough that the site never notices me.

## Limitations

- Selectors depend on the site's current markup; if the site is redesigned, pages will be reported as failed or invalid rather than silently wrong.
- Only 60 of the site's ~1000 books are collected, by design.
- Retry logic is deliberately simple (one retry, fixed wait). Backoff, `Retry-After` and structured logs are next week's assignment (A16).

## Tests

17 offline tests (`tests/`): price normalization, relative→absolute URLs, duplicate URLs, missing description, malformed page, user-agent/timeout/cache, retry rules (500 retried once, 404/403 never), delay only on real requests, and a full idempotent run against a local mock of the site (`tests/mock_site.py`).
