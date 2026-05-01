import yfinance as yf
import pandas as pd
import time
import logging
from pathlib import Path
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OUT = Path(__file__).parent.parent / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

TICKERS = {
    "indices": ["SPY", "QQQ", "DIA", "IWM", "^VIX", "^TNX",
                "^VVIX", "VXX", "VXZ",           # vol-of-vol + VIX term structure proxy
                "DX-Y.NYB", "HYG", "LQD"],        # dollar index + credit spread proxy
    "sectors": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"],
    "commodities": ["CL=F", "BZ=F", "GC=F", "SI=F", "HG=F", "NG=F"],
    "nasdaq100": [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "ADBE", "QCOM", "PEP", "CSCO", "TMUS", "INTC", "INTU", "AMAT",
        "TXN", "AMGN", "HON", "SBUX", "MDLZ", "GILD", "ADI", "REGN", "VRTX", "ISRG",
        "LRCX", "MU", "KLAC", "MRVL", "PANW", "CDNS", "SNPS", "ASML", "MELI", "ABNB",
        "CRWD", "ORLY", "PYPL", "CTAS", "NXPI", "WDAY", "FTNT", "MNST", "PAYX", "ODFL",
        "ROST", "KHC", "FAST", "DXCM", "CPRT", "AEP", "EXC", "XEL", "WBD", "SIRI",
        "PCAR", "IDXX", "BIIB", "ILMN", "MRNA", "ZS", "TTWO", "TEAM", "DDOG", "COIN",
        "APP", "PLTR", "CEG", "ON", "MCHP", "SMCI", "ARM", "DASH", "TTD", "SNOW",
    ],
}

ALL_TICKERS = sum(TICKERS.values(), [])


def download_with_retry(tickers: list, retries: int = 3, delay: int = 5) -> pd.DataFrame:
    for attempt in range(1, retries + 1):
        try:
            log.info(f"Downloading {len(tickers)} tickers (attempt {attempt}/{retries})")
            data = yf.download(
                tickers,
                period="1y",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
            if data.empty:
                raise ValueError("Empty dataframe returned")
            log.info("Download successful")
            return data
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError(f"All {retries} download attempts failed")


def main():
    today = date.today().isoformat()
    out_path = OUT / f"{today}_market_prices.csv"

    if out_path.exists():
        log.info(f"Data already exists for {today}: {out_path}")
        return

    data = download_with_retry(ALL_TICKERS)
    data.to_csv(out_path)
    log.info(f"Saved → {out_path}")
    log.info(f"Shape: {data.shape}")


if __name__ == "__main__":
    main()
