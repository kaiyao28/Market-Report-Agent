import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


def load_price_file(today: str) -> pd.DataFrame:
    path = DATA_DIR / f"{today}_market_prices.csv"
    if not path.exists():
        raise FileNotFoundError(f"Price file not found: {path}\nRun collect_market_data.py first.")
    df = pd.read_csv(path, header=[0, 1], index_col=0, parse_dates=True)
    log.info(f"Loaded {path} — shape {df.shape}")
    return df


def get_close_volume(df: pd.DataFrame, ticker: str):
    """Extract close and volume series for a ticker, handling yfinance multi-level columns."""
    if ticker not in df.columns.get_level_values(0):
        return None, None
    sub = df[ticker]
    close = sub.get("Close", sub.get("close", None))
    volume = sub.get("Volume", sub.get("volume", None))
    if close is None:
        return None, None
    return close.dropna(), volume.dropna() if volume is not None else None


def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).iloc[-1]


def ytd_return(series: pd.Series) -> float:
    current_year = series.index[-1].year
    year_start = series[series.index.year == current_year]
    if len(year_start) < 2:
        return np.nan
    return series.iloc[-1] / year_start.iloc[0] - 1


def calc_ticker(df: pd.DataFrame, ticker: str) -> dict | None:
    close, volume = get_close_volume(df, ticker)
    if close is None or len(close) < 22:
        return None

    last = close.iloc[-1]

    def safe_ret(n):
        if len(close) <= n:
            return np.nan
        return last / close.iloc[-(n + 1)] - 1

    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan

    vol_ratio = np.nan
    if volume is not None and len(volume) >= 20:
        avg_vol = volume.rolling(20).mean().iloc[-1]
        if avg_vol > 0:
            vol_ratio = volume.iloc[-1] / avg_vol

    return {
        "ticker": ticker,
        "last_price": round(last, 4),
        "ret_1d": safe_ret(1),
        "ret_5d": safe_ret(5),
        "ret_20d": safe_ret(20),
        "ytd": ytd_return(close),
        "ma20": round(ma20, 4),
        "ma50": round(ma50, 4) if not np.isnan(ma50) else np.nan,
        "ma200": round(ma200, 4) if not np.isnan(ma200) else np.nan,
        "rsi14": round(rsi(close), 2),
        "volume_ratio": round(vol_ratio, 3) if not np.isnan(vol_ratio) else np.nan,
        "above_20ma": bool(last > ma20),
        "above_50ma": bool(last > ma50) if not np.isnan(ma50) else None,
        "above_200ma": bool(last > ma200) if not np.isnan(ma200) else None,
    }


def main():
    today = date.today().isoformat()
    out_path = DATA_DIR / f"{today}_indicators.csv"

    if out_path.exists():
        log.info(f"Indicators already exist for {today}: {out_path}")
        return

    df = load_price_file(today)
    tickers = df.columns.get_level_values(0).unique().tolist()
    log.info(f"Processing {len(tickers)} tickers")

    rows = []
    failed = []
    for ticker in tickers:
        try:
            row = calc_ticker(df, ticker)
            if row:
                rows.append(row)
        except Exception as e:
            failed.append(ticker)
            log.debug(f"Failed {ticker}: {e}")

    if failed:
        log.warning(f"Skipped {len(failed)} tickers: {failed}")

    result = pd.DataFrame(rows)

    # add volume ratio z-score across all tickers (used for sector_score)
    vr = result["volume_ratio"]
    result["volume_ratio_zscore"] = (vr - vr.mean()) / vr.std()

    # sector_score for sector ETFs
    sector_etfs = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
    mask = result["ticker"].isin(sector_etfs)
    result.loc[mask, "sector_score"] = (
        0.5 * result.loc[mask, "ret_1d"]
        + 0.3 * result.loc[mask, "ret_5d"]
        + 0.2 * result.loc[mask, "volume_ratio_zscore"]
    )

    result.to_csv(out_path, index=False)
    log.info(f"Saved → {out_path}  ({len(result)} rows)")


if __name__ == "__main__":
    main()
