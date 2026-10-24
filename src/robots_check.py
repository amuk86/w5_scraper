"""Stage 0: request robots.txt exactly once and record what happened."""
import json
from datetime import datetime, timezone

import requests

import config


def check_robots(base_url: str = config.BASE_URL, out_dir=config.OUTPUT_DIR) -> dict:
    url = base_url.rstrip("/") + "/robots.txt"
    result = {"url": url, "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        resp = requests.get(url, headers={"User-Agent": config.USER_AGENT},
                            timeout=config.TIMEOUT_SECONDS)
        result["status"] = resp.status_code
        if resp.status_code == 200:
            result["note"] = "robots.txt found - read it and summarise it in the README"
            result["body"] = resp.text[:2000]
        elif resp.status_code == 404:
            # A missing file is NOT permission - it is just a missing file.
            result["note"] = "no robots file found"
        else:
            result["note"] = f"unexpected status {resp.status_code}; treat as 'unclear', stay cautious"
    except requests.RequestException as exc:
        result["status"] = None
        result["note"] = f"request failed: {type(exc).__name__}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "robots-check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
