from dotenv import load_dotenv

from sqlalchemy import select

from util.database import AsyncSessionLocal
from model.spot import Spot

load_dotenv()

async def get_sub_spots(desc: bool = True):
    """查詢人氣小於 3000 的景點"""
    async with AsyncSessionLocal() as db:
        stmt = select(Spot).where(
            Spot.is_active == True,
            Spot.popularity > 1,
            Spot.popularity < 3000,
        )
        stmt = stmt.order_by(Spot.spot_id.desc() if desc else Spot.spot_id.asc())
        result = await db.execute(stmt)
        return result.scalars().all()


async def get_main_spots(desc: bool = True):
    """查詢人氣大於 3000 的景點"""
    async with AsyncSessionLocal() as db:
        stmt = select(Spot).where(
            Spot.is_active == True,
            Spot.popularity > 3000,
        )
        stmt = stmt.order_by(Spot.spot_id.desc() if desc else Spot.spot_id.asc())
        result = await db.execute(stmt)
        return result.scalars().all()


async def get_spots(top_n: int = 10):
    """前 N 個人氣最高的景點"""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Spot)
            .where(
                Spot.is_active == True,
                Spot.popularity > 1,
            )
            .order_by(Spot.popularity.desc())
            .limit(top_n)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


async def get_spots_filtered(city: str | None = None, limit: int = 800):
    """
    依人氣排序的景點；若提供 city 則在資料庫層以 ILIKE 篩選（部分比對）。
    limit 上限避免一次載入過多筆。
    """
    try:
        cap = int(limit)
    except (TypeError, ValueError):
        cap = 800
    cap = max(1, min(cap, 2000))
    async with AsyncSessionLocal() as db:
        stmt = select(Spot).where(
            Spot.is_active == True,
            Spot.popularity > 1,
        )
        if city and str(city).strip():
            stmt = stmt.where(Spot.city.ilike(f"%{str(city).strip()}%"))
        stmt = stmt.order_by(Spot.popularity.desc()).limit(cap)
        result = await db.execute(stmt)
        return result.scalars().all()
