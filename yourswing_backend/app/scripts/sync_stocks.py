import os
import sys
import pandas as pd
from sqlalchemy import text

# Add the root directory to sys.path so 'app' can be resolved
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import engine


CSV_FILES = [
    {
        "path": "app/data/nifty200.csv",
        "index_name": "NIFTY200"
    },
]


def normalize_symbol(symbol: str):
    symbol = symbol.strip().upper()

    # Add NSE suffix if missing
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol = f"{symbol}.NS"

    return symbol


def sync_csv_to_db():

    csv_symbols = set()

    with engine.begin() as conn:

        # -----------------------------
        # READ ALL CSV FILES
        # -----------------------------
        for file in CSV_FILES:

            path = file["path"]
            index_name = file["index_name"]

            df = pd.read_csv(path)

            # CHANGE COLUMN NAMES IF NEEDED
            # Make sure your CSV has:
            # Symbol, Company Name

            for _, row in df.iterrows():

                symbol = normalize_symbol(row["symbol"])

                company_name = row["company_name"]

                csv_symbols.add(symbol)

                # UPSERT STOCK
                conn.execute(text("""
                    INSERT INTO stocks (
                        symbol,
                        company_name,
                        index_name,
                        is_active
                    )
                    VALUES (
                        :symbol,
                        :company_name,
                        :index_name,
                        TRUE
                    )
                    ON CONFLICT (symbol)
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        index_name = EXCLUDED.index_name,
                        is_active = TRUE,
                        updated_at = CURRENT_TIMESTAMP;
                """), {
                    "symbol": symbol,
                    "company_name": company_name,
                    "index_name": index_name
                })

        # -----------------------------
        # FETCH DB SYMBOLS
        # -----------------------------
        db_result = conn.execute(text("""
            SELECT symbol
            FROM stocks
            WHERE is_active = TRUE
        """))

        db_symbols = {row[0] for row in db_result.fetchall()}

        # -----------------------------
        # FIND REMOVED STOCKS
        # -----------------------------
        removed_symbols = db_symbols - csv_symbols

        # -----------------------------
        # MARK REMOVED STOCKS INACTIVE
        # -----------------------------
        for symbol in removed_symbols:

            conn.execute(text("""
                UPDATE stocks
                SET is_active = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE symbol = :symbol
            """), {
                "symbol": symbol
            })

    print("Stock sync completed successfully")


if __name__ == "__main__":
    sync_csv_to_db()