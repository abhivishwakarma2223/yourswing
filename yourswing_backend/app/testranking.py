from app.ranking_engine import run_full_ranking
from app.database import get_db_connection


report = run_full_ranking(
    db_conn_factory=get_db_connection
)

print("\n")
print("=" * 60)
print("TOP 10 SWING STOCKS")
print("=" * 60)

for idx, stock in enumerate(report.top(10), start=1):

    print(f"""
{idx}. {stock.symbol}

Score           : {stock.score:.2f}
Signal          : {stock.signal}
Latest Price    : {stock.latest_price}
RSI             : {stock.rsi}
Volume Ratio    : {stock.volume_ratio}
ATR %           : {stock.atr_percent}
Breakout        : {stock.breakout}
Market Bullish  : {stock.market_bullish}
Trend Alignment : {stock.trend_alignment}

Component Scores:
{stock.component_scores}

--------------------------------------------------
""")

print("\n")
print("=" * 60)
print("SUMMARY")
print("=" * 60)

print(report.summary())

print("\n")
print("=" * 60)
print("ERRORS")
print("=" * 60)

for err in report.errors[:10]:

    print(f"""
Symbol : {err.symbol}
Stage  : {err.stage}
Reason : {err.reason}
Type   : {err.exc_type}
""")