import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# NEW: async SQLAlchemy support
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

# 資料庫連線字符串
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:_5H)6Nm`10fL<1x^@34.81.19.52/postgres"
)

# --- Sync engine/session (kept for backward compatibility) ---
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Async engine/session ---
# Async SQLAlchemy requires an async driver URL. If DATABASE_URL is sync-style,
# produce a best-effort async URL for psycopg.
if "+psycopg_async" in DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL
elif DATABASE_URL.startswith("postgresql+psycopg://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg_async://", 1)
else:
    # Fallback: assume postgresql and psycopg async dialect.
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg_async://", 1)

async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

# 基類
Base = declarative_base()

