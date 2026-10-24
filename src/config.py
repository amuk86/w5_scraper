"""Central settings for the polite scraper. Change values here, not in the logic."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"

# --- Target: a public practice sandbox (see README, "Target classification") ---
BASE_URL = "https://books.toscrape.com"
START_PATH = "/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3          # scope: first three catalogue pages only

# --- Politeness rules ---
# TODO: put your real repo URL here after you create it on GitHub.
REPO_URL = "https://github.com/YOUR-USERNAME/YOUR-REPO"
USER_AGENT = f"FlyRankInternshipA9/1.0 (+{REPO_URL})"
TIMEOUT_SECONDS = 10             # a request gives up after this long
MIN_DELAY_SECONDS = 0.5          # minimum pause between REAL requests
RETRY_WAIT_SECONDS = 2           # pause before the single retry
