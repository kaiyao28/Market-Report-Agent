# Strategy: AQR Cross-Sectional Momentum

## Source
Asness, C., Moskowitz, T., Pedersen, L. (2012). *Value and Momentum Everywhere*.
Journal of Finance. AQR Momentum Indices published at aqr.com.
Alpha: 2.8% annualised (t-stat 5.74) across 47 of 65 tested factor combinations.

## Concept
Rank all assets in a universe by their past 12-month return (excluding the most recent month to avoid short-term reversal).
Long the top performers, avoid/short the bottom performers.
The "skip last month" rule is key — recent 1-month returns tend to mean-revert.

## Signals (from indicators CSV)

### Momentum Score (cross-sectional)
```
momentum_score = ytd - ret_20d
```
- `ytd` ≈ 4-month return (year-to-date, since we're in April)
- Subtracting `ret_20d` (last month) skips the reversal-prone recent period
- Result: longer-term momentum signal, cleaner than raw YTD

### Ranking
Rank all Nasdaq 100 stocks by `momentum_score`:
- **Top 20%** → Strong momentum candidates
- **Bottom 20%** → Weak / avoid

### Quality Filter (combined with momentum)
Only act on top 20% if also:
- `above_50ma = True` (trend intact)
- `rsi14` between 45–75 (not overbought, not collapsing)
- `volume_ratio > 0.9` (reasonable participation)

## Sector Application
Rank sectors by `ret_20d` (20-day as intermediate momentum proxy):
- Top 3 sectors → overweight
- Bottom 3 sectors → underweight / avoid

## Decision Rules
```
momentum_score = ytd - ret_20d

Long candidates: top quintile by momentum_score
  + above_50ma = True
  + 45 < rsi14 < 75

Avoid candidates: bottom quintile by momentum_score
  OR rsi14 > 78 (overbought = reversal risk)
  OR ret_5d < -3% (recent breakdown)
```

## Rebalancing
Monthly. Review rankings at start of each month.
Within month: only add if conviction is strong (all filters pass).
Do not chase intramonth moves.

## Output (for report)
- Top 5 by AQR momentum_score (with score shown)
- Bottom 5 (weakest momentum)
- Sector ranking by intermediate momentum
