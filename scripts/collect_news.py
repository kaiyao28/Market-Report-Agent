"""
Fetches financial news from:
  1. yfinance .news  — for key market tickers (SPY, QQQ, sector ETFs, commodities)
  2. RSS feeds       — Reuters Business, CNBC Markets, MarketWatch
Saves to data/processed/YYYY-MM-DD_news.json
Runs daily, skips if file already exists.
"""

import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (market-report-agent/1.0)"}

RSS_FEEDS = [
    ("CNBC Markets",      "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Economy",      "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("MarketWatch",       "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("Investopedia",      "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline"),
]

YFINANCE_TICKERS = ["SPY", "QQQ", "GC=F", "CL=F", "^VIX",
                    "XLK", "XLF", "XLE", "XLV", "XLI"]


# ── RSS ───────────────────────────────────────────────────────────────────────
def fetch_rss(name: str, url: str, limit: int = 8) -> list[dict]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml-xml")
        items = soup.find_all("item")[:limit]
        results = []
        for item in items:
            pub = item.find("pubDate")
            results.append({
                "source":    name,
                "title":     item.find("title").get_text(strip=True) if item.find("title") else "",
                "link":      item.find("link").get_text(strip=True) if item.find("link") else "",
                "published": pub.get_text(strip=True) if pub else "",
                "summary":   BeautifulSoup(
                                 (item.find("description") or item.find("summary") or item.find("content") or type("", (), {"get_text": lambda *a, **k: ""})()).get_text(strip=True)
                                 if item.find("description") else "", "html.parser"
                             ).get_text(strip=True)[:300],
            })
        log.info(f"  {name}: {len(results)} articles")
        return results
    except Exception as e:
        log.warning(f"  {name} RSS failed: {e}")
        return []


# ── yfinance news ─────────────────────────────────────────────────────────────
def fetch_yf_news(tickers: list[str], per_ticker: int = 5) -> list[dict]:
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance not installed — skipping ticker news")
        return []

    seen = set()
    results = []
    for ticker in tickers:
        try:
            news = yf.Ticker(ticker).news or []
            for item in news[:per_ticker]:
                title = item.get("title", "")
                if title in seen:
                    continue
                seen.add(title)
                ts = item.get("providerPublishTime", 0)
                pub = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M UTC") if ts else ""
                results.append({
                    "source":    item.get("publisher", "Yahoo Finance"),
                    "title":     title,
                    "link":      item.get("link", ""),
                    "published": pub,
                    "summary":   "",
                    "tickers":   item.get("relatedTickers", [ticker]),
                })
            time.sleep(0.3)
        except Exception as e:
            log.debug(f"  yfinance news failed for {ticker}: {e}")

    log.info(f"  yfinance: {len(results)} unique articles across {len(tickers)} tickers")
    return results


# ── categorise ────────────────────────────────────────────────────────────────
MACRO_KEYWORDS    = ["fed", "federal reserve", "inflation", "cpi", "gdp", "rate", "powell",
                     "treasury", "yield", "recession", "jobs", "employment", "fomc"]
ENERGY_KEYWORDS   = ["oil", "crude", "opec", "natural gas", "energy"]
METALS_KEYWORDS   = ["gold", "silver", "copper", "metals", "commodity", "commodities"]
TECH_KEYWORDS     = ["nvidia", "apple", "microsoft", "google", "alphabet", "meta", "amazon",
                     "semiconductor", "ai", "artificial intelligence", "chip"]
RISK_KEYWORDS     = ["war", "geopolit", "sanction", "tariff", "trade", "china", "conflict"]

def categorise(title: str) -> str:
    t = title.lower()
    if any(k in t for k in MACRO_KEYWORDS):   return "Macro / Rates"
    if any(k in t for k in RISK_KEYWORDS):    return "Geopolitical / Risk"
    if any(k in t for k in ENERGY_KEYWORDS):  return "Energy"
    if any(k in t for k in METALS_KEYWORDS):  return "Metals / Commodities"
    if any(k in t for k in TECH_KEYWORDS):    return "Technology"
    return "Markets"


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    today    = date.today().isoformat()
    out_path = DATA_DIR / f"{today}_news.json"

    if out_path.exists():
        log.info(f"News already collected for {today}: {out_path}")
        return

    log.info("Fetching news…")
    articles = []

    # RSS feeds
    for name, url in RSS_FEEDS:
        articles += fetch_rss(name, url)
        time.sleep(0.5)

    # yfinance ticker news
    articles += fetch_yf_news(YFINANCE_TICKERS)

    # deduplicate by title similarity (simple: exact title match)
    seen, unique = set(), []
    for a in articles:
        key = a["title"].lower().strip()[:80]
        if key and key not in seen:
            seen.add(key)
            a["category"] = categorise(a["title"])
            unique.append(a)

    # sort by category
    unique.sort(key=lambda x: x["category"])

    payload = {"date": today, "count": len(unique), "articles": unique}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info(f"Saved {len(unique)} articles → {out_path}")


if __name__ == "__main__":
    main()
