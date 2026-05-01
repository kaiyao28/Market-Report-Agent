# Strategy: Momentum Rotation

## Use When
- Market trend is **Bullish** or **Neutral** (from technical_analysis skill)
- SPY and QQQ both above 50MA
- VIX below 25 and not spiking

## Rules

### Sector Selection
1. Use top 3 sectors by `sector_score` from sector_flow skill.
2. Prefer sectors with both positive `ret_1d` AND `ret_5d`.
3. Avoid sectors showing high volume + negative return (outflow signal).

### Stock Selection
Within top sectors, prefer stocks with:
- `ytd` > 0
- `ret_5d` > 0
- `above_50ma = True`
- `rsi14` between 50–75 (momentum without being overbought)
- `volume_ratio` > 1.0 (above-average participation)

### Downgrade Trigger
- If SPY **or** QQQ drops below 50MA → downgrade all long ideas to watchlist only.
- If VIX rises > 20% in a single day → pause new entries, reassess.

## Output
- **Bullish candidates**: 2–3 stocks/ETFs meeting all criteria
- **Watchlist candidates**: meeting most criteria but RSI > 75 or sector rank 4–6
- **Avoid / overheated**: RSI > 80 or sector showing outflow signal
