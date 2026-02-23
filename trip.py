from mcp.server.fastmcp import FastMCP

from src.action import get_sub_spots, get_main_spots, get_spots
from src.serialization import serialize_spots

import asyncio, json

# Initialize FastMCP server
mcp = FastMCP("trip")


def _safe_int(x, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _safe_get_popularity(spot: dict) -> int:
    for k in ("popularity", "人氣", "人氣數", "hot", "score"):
        v = spot.get(k)
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
    return 0

def _contains_keyword(spot: dict, keyword: str) -> bool:
    if not keyword:
        return True
    kw = keyword.lower()
    for k in ("name", "title", "景點", "spot_name", "description", "desc"):
        v = spot.get(k)
        if isinstance(v, str) and kw in v.lower():
            return True
    return False

@mcp.tool(
    name="major_views",
    description="拿取主要景點，人氣數大於 3000 數，旅遊景點最多可接受 3 個主要景點，最低 1 個。"
)
async def major_views() -> str:
    """Return JSON data for the primary overview spots using `get_main_spots`."""

    data = await get_main_spots()
    return serialize_spots(data)

@mcp.tool(
    name="sub_views",
    description="拿取次要景點，人氣數小於 3000 數。每個主要景點間最少 0 個次要景點，最多 2 個次要景點。"
)
async def sub_views() -> str:
    """Return JSON data for secondary spots from `get_sub_spots`."""

    data = await get_sub_spots()
    return serialize_spots(data)

@mcp.tool(
    name="top_10_spots",
    description="拿取前十個主要景點。"
)
async def get_top_10() -> str:
    """Return a JSON list of the top ten spots produced by `get_spots`."""

    data = await get_spots()
    return serialize_spots(data)

mcp.tool(
    name="spots_by_popularity_range",
    description="依人氣區間過濾景點（min_pop/max_pop），回傳符合的列表。"
)
async def spots_by_popularity_range(min_pop: int = 0, max_pop: int = 10**9) -> str:
    data = await get_spots()
    min_pop = _safe_int(min_pop, 0)
    max_pop = _safe_int(max_pop, 10**9)
    if max_pop < min_pop:
        min_pop, max_pop = max_pop, min_pop
    filtered = [s for s in data if min_pop <= _safe_get_popularity(s) <= max_pop]
    return serialize_spots(filtered)

@mcp.tool(
    name="mix_main_and_sub",
    description="混合主要/次要景點：main_n=1..3；sub_n=0..2。"
)
async def mix_main_and_sub(main_n: int = 2, sub_n: int = 1) -> str:
    main_data, sub_data = await asyncio.gather(get_main_spots(), get_sub_spots())
    main_n = max(1, min(3, _safe_int(main_n, 2)))
    sub_n = max(0, min(2, _safe_int(sub_n, 1)))
    mixed = (main_data[:main_n] or []) + (sub_data[:sub_n] or [])
    return serialize_spots(mixed)

@mcp.tool(
    name="search_spots",
    description="用關鍵字搜尋景點（比對 name/title/description 等常見欄位），回傳前 limit 筆。"
)
async def search_spots(keyword: str, limit: int = 10) -> str:
    data = await get_spots()
    limit = max(1, min(50, _safe_int(limit, 10)))
    matched = [s for s in data if _contains_keyword(s, keyword)]
    return serialize_spots(matched[:limit])

@mcp.tool(
    name="spots_summary",
    description="回傳景點資料摘要（count、min/max/avg 人氣），用於快速檢視資料分佈。"
)
async def spots_summary() -> str:
    data = await get_spots()
    pops = [_safe_get_popularity(s) for s in data]
    count = len(pops)
    if count == 0:
        return json.dumps({"count": 0, "min": None, "max": None, "avg": None}, ensure_ascii=False)
    return json.dumps(
        {
            "count": count,
            "min": min(pops),
            "max": max(pops),
            "avg": sum(pops) / count,
        },
        ensure_ascii=False,
    )

async def main():
    # Use run_async() in async contexts
    await mcp.run_stdio_async()

if __name__ == "__main__":
    """CLI entrypoint.

        Important: some hosted runtimes (including FastMCP Cloud) already have an asyncio
        event loop running. In that case, calling the synchronous `mcp.run(...)` will
        raise: "Already running asyncio in this thread".

        This function therefore:
        - uses `mcp.run(...)` when no loop is running (normal local CLI usage)
        - otherwise schedules the corresponding async runner on the existing loop
        """

    asyncio.run(main())
    #
    # try:
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     loop = None
    #
    # if loop and loop.is_running():
    #     # We're in a runtime that already owns the event loop.
    #     # FastMCP provides transport-specific async runners.
    #     loop.create_task(mcp.run_stdio_async())
    # else:
    #     # No running loop: let FastMCP manage the loop lifecycle.
    #     mcp.run()