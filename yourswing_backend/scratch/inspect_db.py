import os
from sqlalchemy import create_engine, inspect

database_url = "postgresql+psycopg://neondb_owner:npg_SBH1kxVd3jqp@ep-green-pond-ao5salhp-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

try:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    
    for table in tables:
        print(f"\nTable: {table}")
        # Try to find a date column
        columns = inspector.get_columns(table)
        print(f"Columns: {[c['name'] for c in columns]}")
except Exception as e:
    print(f"Error: {e}")
