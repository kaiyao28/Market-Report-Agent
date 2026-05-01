"""
Fetches S&P 500 valuation metrics from free public sources.
Runs daily but only re-fetches when snapshot is older than REFRESH_DAYS.

Sources:
  - multpl.com  : trailing PE, Shiller CAPE
  - FRED        : Market Cap / GDP (Buffett indicator)  [optional, needs FRED_API_KEY env var]
"""

import json
import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_PATH = DATA_DIR / "valuation_snapshot.json"

REFRESH_DAYS = 7
HEADERS = {"User-Agent": "Mozilla/5.0 (research/market-report-agent)"}


# ── helpers ──────────────────────────────────────────────────────────────────

def load_snapshot() -> dict:
    if SNAPSHOT_PATH.exists():
        with open(SNAPSHOT_PATH) as f:
            return json.load(f)
    return {}


def is_stale(snapshot: dict) -> bool:
    updated = snapshot.get("updated")
    if not updated:
        return True
    age = (date.today() - datetime.fromisoformat(updated).date()).days
    return age >= REFRESH_DAYS


def save_snapshot(data: dict):
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Saved valuation snapshot → {SNAPSHOT_PATH}")


def fetch_multpl(path: str) -> float | None:
    """Scrape the current value from a multpl.com page."""
    import re
    url = f"https://www.multpl.com/{path}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        val = soup.find(id="current")
        if val:
            text = val.get_text(strip=True).replace(",", "")
            match = re.search(r"[\d]+\.[\d]+", text)
            if match:
                return float(match.group())
    except Exception as e:
        log.warning(f"multpl fetch failed ({path}): {e}")
    return None


def fetch_fred(series_id: str) -> float | None:
    """Fetch latest value from FRED. Requires FRED_API_KEY env var."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        log.info("FRED_API_KEY not set — skipping Market Cap/GDP fetch")
        return None
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
        f"&sort_order=desc&limit=1"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if obs and obs[0]["value"] != ".":
            return float(obs[0]["value"])
    except Exception as e:
        log.warning(f"FRED fetch failed ({series_id}): {e}")
    return None


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    snapshot = load_snapshot()

    if not is_stale(snapshot):
        age = (date.today() - datetime.fromisoformat(snapshot["updated"]).date()).days
        log.info(f"Valuation snapshot is {age}d old — no update needed (refresh every {REFRESH_DAYS}d)")
        return

    log.info("Valuation snapshot is stale — fetching fresh data")

    trailing_pe = fetch_multpl("s-p-500-pe-ratio")
    time.sleep(1)
    shiller_cape = fetch_multpl("shiller-pe")
    time.sleep(1)
    # DDDM01USA156NWDB = Mkt Cap / GDP for USA (annual, so may lag)
    mkt_cap_gdp = fetch_fred("DDDM01USA156NWDB")

    new_snapshot = {
        "updated": date.today().isoformat(),
        "sp500_trailing_pe": trailing_pe,
        "sp500_forward_pe": None,   # no reliable free source
        "sp500_shiller_cape": shiller_cape,
        "nasdaq_forward_pe": None,  # no reliable free source
        "market_cap_to_gdp": mkt_cap_gdp,
        "notes": (
            "trailing_pe + shiller_cape: multpl.com | "
            "market_cap_to_gdp: FRED DDDM01USA156NWDB (annual, may lag) | "
            "forward_pe: not available from free sources"
        ),
    }

    for k, v in new_snapshot.items():
        if k not in ("updated", "notes") and v is None:
            log.warning(f"  {k}: fetch failed — will show as missing in report")
        elif k not in ("updated", "notes"):
            log.info(f"  {k}: {v}")

    save_snapshot(new_snapshot)


if __name__ == "__main__":
    main()
