"""Polite HTTP fetching: honest user-agent, timeout, status check, delay, cache, one retry."""
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

import config


class FetchError(Exception):
    """A page could not be fetched. Carries the URL, a reason and (if any) the status code."""

    def __init__(self, url, reason, status=None):
        super().__init__(f"{url}: {reason}")
        self.url, self.reason, self.status = url, reason, status


@dataclass
class FetchResult:
    url: str
    html: str
    from_cache: bool
    fetched_at: str          # ISO-8601 UTC: when the bytes were really downloaded
    size: int                # response size in bytes


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PoliteFetcher:
    def __init__(self, cache_dir=config.CACHE_DIR, delay=config.MIN_DELAY_SECONDS,
                 timeout=config.TIMEOUT_SECONDS, user_agent=config.USER_AGENT,
                 retry_wait=config.RETRY_WAIT_SECONDS, session=None,
                 sleep=time.sleep, clock=time.monotonic):
        self.cache_dir = Path(cache_dir)
        self.delay, self.timeout, self.retry_wait = delay, timeout, retry_wait
        self.headers = {"User-Agent": user_agent}
        self.session = session or requests.Session()
        self._sleep, self._clock = sleep, clock
        self._last_request = None
        # counters used by the run report
        self.network_fetches = 0
        self.cache_hits = 0
        self.retries = 0

    # ---- cache -----------------------------------------------------------
    def cache_path(self, url: str) -> Path:
        """catalogue/page-1.html -> cache/catalogue-page-1.html"""
        path = urlparse(url).path.strip("/") or "index.html"
        name = re.sub(r"[^A-Za-z0-9._-]", "_", path.replace("/", "-"))
        return self.cache_dir / name

    # ---- politeness ------------------------------------------------------
    def _wait_turn(self):
        """Only REAL requests wait. Cache hits never come through here."""
        if self._last_request is not None:
            remaining = self.delay - (self._clock() - self._last_request)
            if remaining > 0:
                self._sleep(remaining)

    # ---- public API ------------------------------------------------------
    def get(self, url: str) -> FetchResult:
        path = self.cache_path(url)
        if path.exists():
            data = path.read_bytes()
            self.cache_hits += 1
            return FetchResult(url, data.decode("utf-8", errors="replace"), True,
                               _iso(path.stat().st_mtime), len(data))
        data = self._download(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)                      # never leave a half-written cache file
        return FetchResult(url, data.decode("utf-8", errors="replace"), False,
                           _iso(time.time()), len(data))

    def _download(self, url: str) -> bytes:
        """Try once; retry ONCE on timeout / connection error / 5xx. Never retry 4xx."""
        reason, status = "unknown", None
        for attempt in (1, 2):
            self._wait_turn()
            try:
                resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                reason, status = f"{type(exc).__name__}", None
            else:
                status = resp.status_code
                if status == 200:
                    self.network_fetches += 1
                    return resp.content          # raw bytes: we decode as UTF-8 ourselves
                reason = f"HTTP {status}"
                if status < 500:                 # 404 / 403 / 429...: asking again will not help
                    raise FetchError(url, reason, status)
            finally:
                self._last_request = self._clock()
            if attempt == 1:
                self.retries += 1
                self._sleep(self.retry_wait)
        raise FetchError(url, f"{reason} (gave up after retry)", status)
