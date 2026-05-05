import yfinance as yf


def fetch_daily_candles(symbol: str):

    stock = yf.Ticker(symbol)

    df = stock.history(period="1y", interval="1d")

    candles = []

    for index, row in df.iterrows():

        candles.append({
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume": row["Volume"],
            "candle_time": index
        })

    return candles