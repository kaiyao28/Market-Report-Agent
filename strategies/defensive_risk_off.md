# Strategy: Defensive / Risk-Off

## Use When
- Market trend is **Caution** or **Bearish** (from technical_analysis skill)
- SPY or QQQ below 50MA
- VIX > 25 or rising sharply (> 15% in 5D)
- Gold rising while equities falling

## Rules

### Sector Rotation to Defensive
Prefer these sectors in risk-off:
1. **XLP** — Consumer Staples (non-cyclical demand)
2. **XLU** — Utilities (dividend / low beta)
3. **XLV** — Health Care (recession-resistant)
4. **XLB** — Materials (if commodity cycle is supportive)

Avoid or reduce:
- XLK, XLY, XLRE — high-beta / rate-sensitive
- XLF — financials underperform in stress scenarios

### Commodity Hedge Signal
- Gold (`GC=F`) above 20MA + rising → risk-off confirmed, defensive posture warranted
- Silver + Gold both rising → amplified safe-haven signal
- Oil falling while gold rising → demand concern, not just inflation hedge

### Cash / Flat Signal
If ALL of these are true:
- SPY below 200MA
- VIX > 30
- Gold rising > 2% in 5D
→ Flag "consider reducing exposure / raising cash" in report.

### Stock Criteria in Risk-Off
- `above_200ma = True` (quality filter)
- Low `rsi14` (< 50) — not already extended
- `ret_5d` outperforming SPY `ret_5d` (relative strength)
- Dividend-paying or low-beta preferred

## Output
- Risk-off signal: [Mild / Moderate / Strong]
- Defensive sector picks: up to 3 ETFs or stocks
- Hedge note: gold/VIX interpretation
- Cash signal: Yes / No with reason
