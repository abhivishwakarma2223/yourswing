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
    yield
    logger.info("Application shutting down...")

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

Base.metadata.create_all(bind=engine)

app.include_router(candle_routes.router)

@app.get("/")
def read_root():
    return {"message": "app is running ...."}
