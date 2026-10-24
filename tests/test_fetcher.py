import requests

from fetcher import FetchError, PoliteFetcher


class Resp:
    def __init__(self, status, body=b"<html>ok</html>"):
        self.status_code, self.content = status, body


class FakeSession:
    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers, timeout))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def make(tmp_path, *outcomes, delay=0.5):
    sleeps = []
    f = PoliteFetcher(cache_dir=tmp_path, delay=delay, retry_wait=2, session=FakeSession(*outcomes),
                      sleep=sleeps.append, clock=lambda: 0.0)
    return f, sleeps


def test_sends_user_agent_and_timeout_then_caches(tmp_path):
    f, _ = make(tmp_path, Resp(200))
    first = f.get("https://x.test/catalogue/page-1.html")
    second = f.get("https://x.test/catalogue/page-1.html")
    assert not first.from_cache and second.from_cache
    _, headers, timeout = f.session.calls[0]
    assert "FlyRankInternshipA9" in headers["User-Agent"] and timeout
    assert len(f.session.calls) == 1 and (tmp_path / "catalogue-page-1.html").exists()


def test_404_is_not_retried_and_not_cached(tmp_path):
    f, _ = make(tmp_path, Resp(404))
    try:
        f.get("https://x.test/nope.html")
        assert False
    except FetchError as e:
        assert e.status == 404
    assert len(f.session.calls) == 1 and f.retries == 0 and not list(tmp_path.iterdir())


def test_403_is_not_retried(tmp_path):
    f, _ = make(tmp_path, Resp(403))
    try:
        f.get("https://x.test/a.html")
    except FetchError as e:
        assert e.status == 403
    assert len(f.session.calls) == 1


def test_500_retried_once_then_succeeds(tmp_path):
    f, sleeps = make(tmp_path, Resp(500), Resp(200))
    assert f.get("https://x.test/a.html").html == "<html>ok</html>"
    assert f.retries == 1 and 2 in sleeps


def test_timeout_retried_once_then_gives_up(tmp_path):
    f, _ = make(tmp_path, requests.Timeout(), requests.Timeout())
    try:
        f.get("https://x.test/a.html")
        assert False
    except FetchError as e:
        assert "gave up" in e.reason
    assert len(f.session.calls) == 2           # one try + exactly one retry


def test_delay_between_real_requests_only(tmp_path):
    f, sleeps = make(tmp_path, Resp(200), Resp(200))
    f.get("https://x.test/a.html")
    f.get("https://x.test/b.html")
    assert 0.5 in sleeps                       # waited before the second REAL request
    sleeps.clear()
    f.get("https://x.test/a.html")             # cache hit
    assert sleeps == []


def test_utf8_pound_sign_survives(tmp_path):
    f, _ = make(tmp_path, Resp(200, "£51.77".encode("utf-8")))
    assert f.get("https://x.test/a.html").html == "£51.77"
