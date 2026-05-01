# Skill: YTD Stock Ranking

## Goal
Find the strongest US stocks year-to-date within the Nasdaq 100 universe.

## Universe
Nasdaq 100 tickers (collected by `collect_market_data.py`).
Optional: expand to S&P 500 if data is available in indicators CSV.

## Metrics (from indicators CSV)
- `ytd`: year-to-date return
- `ret_1m` (approximated by `ret_20d`)
- `ret_5d`: past week return
- `rsi14`: momentum health check
- `above_50ma`: trend filter
- `volume_ratio`: conviction filter

## Ranking Logic
1. Filter out tickers with < 60 days of data.
2. Sort by `ytd` descending → Top 20 YTD leaders.
3. From those Top 20, find Top 10 also improving on `ret_5d` (positive and > median).
4. Flag stocks with strong YTD but weakening 5D trend:
   - `ytd` > 15% AND `ret_5d` < -2% → "YTD leader losing momentum"

## Quality Filters
- Exclude if `rsi14` > 80 from actionable list (overbought — watchlist only)
- Prefer stocks `above_50ma = True` for momentum continuation
- Volume ratio > 1.1 adds conviction signal

## Output Format
**Top 20 YTD Leaders:**
```
Rank | Ticker | YTD % | 5D % | RSI | vs 50MA | Volume Ratio | Signal
```

**Top 10 Improving This Week** (subset of above with strong 5D):
```
Ticker | YTD % | 5D % | Signal
```

**YTD Leaders Losing Steam:**
```
Ticker | YTD % | 5D % | Note
```
