def generate_signal(indicators: dict):
    rsi = indicators.get("RSI", 0)
    ema20 = indicators.get("EMA20", 0)
    ema50 = indicators.get("EMA50", 0)
    macd = indicators.get("MACD", 0)
    macd_signal = indicators.get("MACD_SIGNAL", 0)
    volume_ratio = indicators.get("VOLUME_RATIO", 0)
    breakout = indicators.get("BREAKOUT", False)

    # Basic trend and momentum check
    if ema20 > ema50 and rsi > 50:g
    
        # Stronger confirmation for BUY
        if (macd > macd_signal or breakout) and volume_ratio > 1.0:
            return "BUY"
        return "WATCH"

    if ema20 < ema50 or rsi < 40:
        return "AVOID"

    return "WATCH"