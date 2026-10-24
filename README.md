# The polite scraper (FlyRank A9)

A small, polite scraping pipeline for **Books to Scrape**.

## Target classification

- **Site:** https://books.toscrape.com
- **Why:** [toscrape.com](https://toscrape.com) describes its sites as sandboxes built for people to practise scraping on. That statement is my permission.
- **How much:** the first 3 catalogue pages only (60 books), plus each book's own page.
- **Data collected:** title, product URL, price text, availability text, star rating, description (when present).
- **robots.txt result:** _run `python src/main.py robots` and paste the result here (status code + one line on what it said, or "no robots file found")._
- **Why this is appropriate:** it is a public practice sandbox, the volume is tiny (about 63 requests), and I identify myself and go slowly.

I will not reuse this code on another site without checking its rules and terms first.
