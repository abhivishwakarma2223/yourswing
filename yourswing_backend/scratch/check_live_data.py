from sqlalchemy import create_engine, text

database_url = "postgresql+psycopg://neondb_owner:npg_SBH1kxVd3jqp@ep-green-pond-ao5salhp-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(database_url)

with engine.connect() as conn:
    print("Checking live_market_state table...")
    result = conn.execute(text("SELECT symbol, live_price, live_change_pct FROM live_market_state LIMIT 5"))
    rows = result.fetchall()
    if not rows:
        print("Table live_market_state is empty!")
    else:
        for row in rows:
            print(row)

    print("\nChecking daily_stock_candidates table...")
    result = conn.execute(text("SELECT symbol, trade_date FROM daily_stock_candidates ORDER BY trade_date DESC LIMIT 5"))
    rows = result.fetchall()
    for row in rows:
        print(row)
