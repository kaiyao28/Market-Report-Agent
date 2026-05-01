# Skill: Valuation Snapshot

## Goal
Provide a weekly valuation context for broad US indices to calibrate risk/reward.

## Data Sources
- GuruFocus: S&P 500 PE, Shiller CAPE, market cap / GDP
- Siblis Research: Forward PE by index
- MacroMicro: Macro valuation overlays
- **Do not scrape aggressively** — check manually once per week, store in `data/processed/valuation_snapshot.json`

## Valuation File Format
Store as `data/processed/valuation_snapshot.json`:
```json
{
  "updated": "YYYY-MM-DD",
  "sp500_trailing_pe": null,
  "sp500_forward_pe": null,
  "sp500_shiller_cape": null,
  "nasdaq_forward_pe": null,
  "market_cap_to_gdp": null,
  "notes": ""
}
```

## Interpretation Benchmarks
| Metric | Cheap | Fair | Stretched | Expensive |
|--------|-------|------|-----------|-----------|
| S&P 500 Forward PE | < 15 | 15–20 | 20–25 | > 25 |
| Shiller CAPE | < 20 | 20–28 | 28–35 | > 35 |
| Mkt Cap / GDP | < 80% | 80–120% | 120–160% | > 160% |

## Behaviour in Report
- If `valuation_snapshot.json` exists and `updated` is within 7 days: use the values.
- If file is missing or stale (> 7 days): write "Valuation data not updated this week — check GuruFocus."
- Never invent valuation numbers.

## Output Format
- S&P 500 trailing PE: X.X
- S&P 500 forward PE: X.X
- Shiller CAPE: X.X
- Nasdaq forward PE: X.X
- Market Cap / GDP: X%
- Valuation comment: [Cheap / Fair / Stretched / Expensive] — 1 sentence context
