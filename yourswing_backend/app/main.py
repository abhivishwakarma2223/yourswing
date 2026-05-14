import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from app.database import engine, Base, SessionLocal
from app.routes import candle_routes
from app.config import settings

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

def _job_daily_snapshot():
    from app.market_api import fetch_all_active_stock_candles
    from app.snapshot_engine import run_daily_snapshot
    
    logger.info("⏰ Scheduler: starting daily candle sync...")
    try:
        fetch_all_active_stock_candles()
        logger.info("⏰ Scheduler: candle sync complete.")
    except Exception as e:
        logger.error(f"⏰ Scheduler: candle sync failed: {e}")

    logger.info("⏰ Scheduler: starting daily snapshot job...")
    db = SessionLocal()
    try:
        result = run_daily_snapshot(db, engine.raw_connection, force=False)
        logger.info(f"⏰ Snapshot job done: {result}")
    except Exception as e:
        db.rollback()
        logger.error(f"⏰ Snapshot job failed: {e}", exc_info=True)
    finally:
        db.close()

def _job_live_update():
    from app.market_update import run_live_update, is_market_open
    if not is_market_open():
        return
    db = SessionLocal()
    try:
        run_live_update(db)
    except Exception as e:
        db.rollback()
        logger.error(f"⏰ Live update failed: {e}", exc_info=True)
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create/Verify tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Verify hybrid tables exist
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM daily_stock_candidates LIMIT 1"))
            conn.execute(text("SELECT 1 FROM live_market_state LIMIT 1"))
        logger.info("Hybrid institutional tables verified.")
    except Exception as e:
        logger.warning(f"Hybrid tables missing or inaccessible: {e}. Running create_tables...")
        from app.create_tables import create_tables
        try:
            create_tables()
        except Exception as e2:
            logger.error(f"Failed to auto-create hybrid tables: {e2}")

    # 2. Start Scheduler
    scheduler = BackgroundScheduler(timezone=IST)
    
    # Daily Snapshot at 8:00 PM IST
    scheduler.add_job(
        _job_daily_snapshot,
        CronTrigger(hour=20, minute=0, day_of_week='mon-fri', timezone=IST),
        id="daily_snapshot"
    )
    
    # Live Update every minute during market hours (Mon-Fri, 9:00 AM - 4:00 PM IST)
    scheduler.add_job(
        _job_live_update,
        CronTrigger(day_of_week='mon-fri', hour='9-15', minute='*', timezone=IST),
        id="live_update"
    )
    
    scheduler.start()
    logger.info("Background scheduler started.")
    
    yield
    
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candle_routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "YourSwing Hybrid Backend is running."}
