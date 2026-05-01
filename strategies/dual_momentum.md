# Strategy: Dual Momentum (Gary Antonacci)

## Source
Antonacci, G. (2014). *Dual Momentum Investing*. McGraw-Hill.
SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2042750
Performance: 17.4% annual return vs 8.9% buy-and-hold (1974–2013), max drawdown 22.7% vs 60.2%.

## Concept
Two momentum filters applied in sequence:
1. **Absolute Momentum** — Is the asset beating cash? (positive 12-month return)
2. **Relative Momentum** — Is this asset the best among peers?

Both must be positive to hold. If absolute momentum is negative → exit to safety (bonds/cash).

## Signals (computed from indicators CSV)

### Absolute Momentum (SPY)
- Use `ytd` return for SPY as proxy for multi-month absolute momentum.
- If `SPY.ytd > 0` → Absolute momentum **positive** → Risk-on
- If `SPY.ytd < 0` → Absolute momentum **negative** → Risk-off: hold bonds/cash

### Relative Momentum (Sector ranking)
- Rank sectors by `sector_score` (already computed: 0.5×1D + 0.3×5D + 0.2×vol_z)
- For multi-month view: rank sectors by `ret_20d` as proxy for intermediate momentum
- Long top 3 sectors by intermediate momentum when absolute momentum is positive

### Relative Momentum (Stocks)
- Rank Nasdaq 100 universe by `ytd` (YTD return as 12-month proxy)
- Long top quintile when above 50MA and absolute momentum positive

## Decision Rules

```
IF SPY.ytd > 0 (absolute momentum positive):
    → Risk-ON
    → Hold top 3 sectors by ret_20d (intermediate momentum)
    → Hold top YTD stocks that are also above 50MA
    → Apply momentum_rotation.md for stock selection

IF SPY.ytd < 0 (absolute momentum negative):
    → Risk-OFF
    → Exit equities, rotate to defensive (XLP, XLU, XLV, GC=F)
    → Apply defensive_risk_off.md
```

## Monthly Rebalancing Signal
Check on the first trading day of each month:
- Has SPY.ytd flipped sign? → Switch regime
- Has sector ranking changed? → Rotate top 3

## Output (for report)
- Dual Momentum Signal: RISK-ON / RISK-OFF
- Absolute Momentum (SPY YTD): X%
- Top sectors by intermediate momentum (ret_20d rank)
- Regime change alert if SPY YTD near 0% (within ±2%)
