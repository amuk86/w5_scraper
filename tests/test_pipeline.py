import json

import mock_site
import pipeline
from fetcher import PoliteFetcher


def test_full_run_is_idempotent_and_survives_a_bad_url(tmp_path):
    server, base = mock_site.start()
    try:
        out, cache = tmp_path / "output", tmp_path / "cache"
        fake = base + "/catalogue/this-book-does-not-exist_9999/index.html"

        r1 = pipeline.run(base, out, PoliteFetcher(cache_dir=cache, delay=0), extra_urls=[fake])
        books1 = (out / "books.json").read_text(encoding="utf-8")
        assert r1["valid_records"] == 60 and r1["failed_pages"] == 1
        assert r1["pages_fetched"] == 63 and r1["cache_hits"] == 0

        r2 = pipeline.run(base, out, PoliteFetcher(cache_dir=cache, delay=0), extra_urls=[fake])
        assert (out / "books.json").read_text(encoding="utf-8") == books1     # byte-identical rerun
        assert len(json.loads(books1)) == 60
        assert r2["cache_hits"] == 63 and r2["pages_fetched"] == 0
        assert {"started_at", "duration_seconds", "pages_fetched", "cache_hits",
                "valid_records", "invalid_records", "failed_pages"} <= set(r2)
        # every real request identified itself
        assert all("FlyRankInternshipA9" in (ua or "") for _, ua in mock_site.Handler.log)
    finally:
        server.shutdown()


def test_description_missing_stays_null(tmp_path):
    server, base = mock_site.start()
    try:
        pipeline.run(base, tmp_path / "o", PoliteFetcher(cache_dir=tmp_path / "c", delay=0))
        books = json.loads((tmp_path / "o" / "books.json").read_text(encoding="utf-8"))
        assert sum(b["description"] is None for b in books) == 1
        assert all(isinstance(b["price_gbp"], float) for b in books)
    finally:
        server.shutdown()
