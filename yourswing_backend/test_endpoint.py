from app.database import get_db
from app.routes.candle_routes import get_trending_stocks
import pprint

# Create a mock or real DB session
db = next(get_db())

try:
    trending = get_trending_stocks(db)
    pprint.pprint(trending)
finally:
    db.close()
