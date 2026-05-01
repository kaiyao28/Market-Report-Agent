# Strategy: Faber GTAA — Global Tactical Asset Allocation

## Source
Faber, M. (2007). *A Quantitative Approach to Tactical Asset Allocation*.
SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
Performance: Max drawdown reduced 80%, volatility halved vs buy-and-hold across 100+ years of data.

## Concept
Simple timing rule: if an asset's price is **above its 10-month (≈200-day) moving average**, hold it.
If **below**, move to cash or bonds. Applied independently to each asset class.

This is equivalent to the trend-following principle: participate in uptrends, avoid downtrends.

## Signals (computed from indicators CSV)

| Asset | Ticker | Faber Signal |
|-------|--------|-------------|
| US Equities | SPY | `above_200ma` |
| Nasdaq / Tech | QQQ | `above_200ma` |
| Small Caps | IWM | `above_200ma` |
| Gold | GC=F | `above_200ma` |
| Energy | XLE | `above_200ma` |
| REITs | XLRE | `above_200ma` |

### Signal Interpretation
- `above_200ma = True` → **Hold** (trend intact)
- `above_200ma = False` → **Avoid / reduce** (trend broken)

## GTAA Score (daily)
Count how many of the 6 assets above are above their 200MA:
- 5–6 of 6 → **Full risk-on** (broadly bullish trend)
- 3–4 of 6 → **Selective** (hold only those above MA)
- 1–2 of 6 → **Defensive** (most trends broken, raise cash)
- 0 of 6 → **Risk-off** (hold bonds/cash, no equity exposure)

## Decision Rules
```
GTAA_score = count of tracked assets above 200MA

IF GTAA_score >= 5: Full momentum — apply momentum_rotation.md
IF GTAA_score == 3-4: Selective — only hold assets above 200MA
IF GTAA_score <= 2: Defensive — apply defensive_risk_off.md
```

## Rebalancing
- Check monthly (first trading day). Daily monitoring for extreme moves only.
- Do not whipsaw: require 2 consecutive closes above/below 200MA before acting.

## Output (for report)
- GTAA Score: X / 6
- Assets above 200MA: list
- Assets below 200MA: list (reduce/avoid)
- GTAA Regime: Full Risk-On / Selective / Defensive / Risk-Off
