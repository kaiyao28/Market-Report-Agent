# Strategy: Commodity Macro Overlay

## Purpose
Use commodity signals to confirm or challenge the equity market narrative.
Commodities often lead equity sectors — use them as a cross-check, not a standalone signal.

## Core Signal Matrix

| Commodity Pattern | Macro Read | Equity Implication |
|-------------------|------------|--------------------|
| Oil up + Copper up | Global growth demand | Cyclicals, Industrials (XLI, XLB, XLE) |
| Oil up + Copper flat/down | Supply squeeze or geopolitical | Energy (XLE) only; caution on broad cyclicals |
| Gold up + equities down | Risk-off / flight to safety | Defensive posture (see defensive_risk_off.md) |
| Gold up + equities up | Inflation hedge accumulation | Monitor — may reverse |
| Copper down + Oil down | Demand concern / slowdown | Reduce cyclical exposure |
| Natural gas spike | Energy sector specific | XLE short-term, not macro |
| Gold up + Copper up + Oil up | Broad commodity bull / inflation | Real assets, commodities ETFs; caution on tech |

## How to Apply in Report

### Step 1: Read commodity signals
From commodities skill output — note which are above 20MA and 50MA.

### Step 2: Cross-check vs equity trend
- If equity trend is **Bullish** but commodities (copper, oil) are falling → flag divergence.
- If equity trend is **Bearish** but copper is rising → possible growth re-acceleration signal.

### Step 3: Assign overlay label
- **Confirming bullish**: Copper + Oil rising, Gold stable/down
- **Confirming bearish**: Copper + Oil falling, Gold rising
- **Divergence — monitor**: Mixed signals, do not force a call
- **Inflationary**: Oil + Gold both rising, confirm with CPI context if available

## Output
- Commodity macro signal: [Confirming Bullish / Confirming Bearish / Divergence / Inflationary]
- Key driver commodity: [name the leading mover]
- Implication for equity strategy: 1 sentence
