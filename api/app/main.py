from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

from app.db import init_db, AsyncSessionLocal
from app.routers import markets, flags, comparison, promotion
from app.seed import seed_india_market

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Feature Flag Promotion Dashboard",
    description="POC for market-aware feature flag promotion",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets.router, prefix="/api/v1")
app.include_router(flags.router, prefix="/api/v1")
app.include_router(comparison.router, prefix="/api/v1")
app.include_router(promotion.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting application...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        await seed_india_market(session)
    
    logger.info("Application started successfully")


@app.get("/")
async def root():
    return {"message": "Feature Flag Promotion Dashboard API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
