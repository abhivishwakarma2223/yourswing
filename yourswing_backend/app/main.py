from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes import candle_routes
from app.config import settings
from contextlib import asynccontextmanager
import logging
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from app.market_api import fetch_all_active_stock_candles

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Connecting to database at {settings.DATABASE_URL}")
    try:
        # Create database tables safely during startup
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection successful. Tables created.")
    except OperationalError as e:
        logger.error(f"Failed to connect to the database! Please check your PostgreSQL server and credentials. Error: {e}")
        # We don't crash here, allowing FastAPI to still boot up so you can see the logs
    except Exception as e:
        logger.error(f"An unexpected database error occurred: {e}")
        
    # Start the Background Scheduler
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Kolkata"))
    # Schedule to run at 4:00 PM IST (16:00) every weekday (Monday-Friday)
    scheduler.add_job(
        fetch_all_active_stock_candles,
        'cron',
        day_of_week='mon-fri',
        hour=16,
        minute=0,
        id="sync_daily_candles",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background scheduler started: Daily candle sync scheduled for 16:00 IST (Mon-Fri).")
    
    yield
    
    scheduler.shutdown()
    logger.info("Application and scheduler shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend for swing trading application, serving stock candles for mobile app.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base.metadata.create_all(bind=engine)  # Removed redundant call; handled in lifespan

app.include_router(candle_routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "app is running ...."}
