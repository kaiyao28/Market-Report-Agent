# Skill: Sector Flow Analysis

## Goal
Identify which US sectors had the strongest inflow/outflow behaviour over the last trading day and past week.

## Inputs
- Sector ETFs: XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC
- Price change: 1D, 5D, 20D
- Volume change vs 20-day average

## Method
1. Calculate 1D and 5D returns for each sector ETF.
2. Calculate volume ratio: `today_volume / 20d_avg_volume`
3. Compute volume ratio z-score across all sectors for that day.
4. Rank sectors by composite score:
   ```
   sector_score = 0.5 * ret_1d + 0.3 * ret_5d + 0.2 * volume_ratio_zscore
   ```
5. Label each sector:
   - **Strong inflow proxy**: positive return + volume ratio > 1.2
   - **Outflow proxy**: negative return + volume ratio > 1.2
   - **Weak rotation**: small move + volume ratio near 1.0

## Output
- Top 3 strongest sectors with ETF, 1D%, 5D%, volume ratio, signal
- Top 3 weakest sectors with same fields
- Sector rotation interpretation (1–2 sentences)
- Best 3 stocks inside the strongest sectors (from indicators data, ranked by ret_1d within sector)

## Sector → ETF Map
| Sector | ETF |
|--------|-----|
| Technology | XLK |
| Financials | XLF |
| Energy | XLE |
| Health Care | XLV |
| Industrials | XLI |
| Consumer Discretionary | XLY |
| Consumer Staples | XLP |
| Utilities | XLU |
| Materials | XLB |
| Real Estate | XLRE |
| Communication Services | XLC |
