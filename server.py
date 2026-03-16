from fastmcp import FastMCP
import asyncio, json
from src.action import get_sub_spots, get_main_spots, get_spots
from src.serialization import serialize_spots

mcp = FastMCP(name="trip")


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


def _extract_text_fields(spot: dict) -> str:
    """把景點常見文字欄位合併成一個字串，方便做風格關鍵字比對。"""
    parts: list[str] = []
    for k in ("name", "title", "景點", "spot_name", "description", "desc", "category", "類別"):
        v = spot.get(k)
        if isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def _get_styles_for_spot(spot: dict) -> set[str]:
    """
    依據 name/description/category 關鍵字，推估景點適合的旅遊風格。
    這是啟發式規則，重點是讓 LLM 更容易拿到一組「風格標籤」來用。
    """
    text = _extract_text_fields(spot)
    text_lower = text.lower()
    styles: set[str] = set()

    # 文青
    if any(k in text for k in ["文青", "藝文", "展覽", "博物館", "美術館", "文創", "書店", "咖啡", "咖啡廳"]):
        styles.add("文青")

    # 親子
    if any(k in text for k in ["親子", "動物園", "樂園", "遊樂", "兒童", "小朋友", "水族館", "農場", "親子館"]):
        styles.add("親子")

    # 自然
    if any(k in text for k in ["山", "森林", "步道", "國家公園", "海", "海灘", "沙灘", "湖", "溪谷", "瀑布", "溫泉", "自然"]):
        styles.add("自然")

    # 美食
    if any(k in text for k in ["美食", "小吃", "夜市", "餐廳", "市場", "點心", "甜點", "咖啡", "早午餐"]):
        styles.add("美食")

    # 歷史
    if any(k in text for k in ["古蹟", "歷史", "老街", "老城", "廟", "寺", "祠", "遺址", "城門"]):
        styles.add("歷史")

    # 網美
    if any(k in text for k in ["網美", "打卡", "拍照", "景觀台", "觀景台", "天空步道", "天空之鏡", "彩虹", "裝置藝術"]):
        styles.add("網美")

    # 雨天備案（以室內、商場型態為主）
    if any(k in text for k in ["室內", "購物中心", "百貨", "商場", "outlet", "博物館", "水族館", "展覽"]):
        styles.add("雨天備案")

    # 若實在沒有對到任何關鍵字，就留空集合，交給上層 fallback
    return styles



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


@mcp.tool(
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
    name="get_spots_by_trip_style",
    description=(
        "依旅遊風格推薦景點。例如：文青、親子、自然、美食、歷史、網美、雨天備案。"
        "可選填 city 與 limit，讓 LLM 比純關鍵字搜尋更貼近真實聊天需求。"
    ),
)
async def get_spots_by_trip_style(trip_style: str, city: str | None = None, limit: int = 20) -> str:
    """
    依據啟發式「旅遊風格標籤」回傳景點列表。
    - trip_style: 期望的風格（例如「文青」「親子」「自然」等）。
    - city: 可選，城市名稱；若有提供只回傳該城市的景點。
    - limit: 回傳筆數上限。
    """
    # 撈比較多一點，讓風格/城市過濾有空間
    data = await get_spots(top_n=500)
    norm_style = (trip_style or "").strip()
    limit = max(1, min(100, _safe_int(limit, 20)))

    results = []
    for spot in data:
        spot_dict = {
            "spot_id": getattr(spot, "spot_id", None),
            "name": getattr(spot, "name", None),
            "description": getattr(spot, "description", None),
            "popularity": getattr(spot, "popularity", None),
            "is_active": getattr(spot, "is_active", None),
            "city": getattr(spot, "city", None),
            "category": getattr(spot, "category", None),
        }

        styles = _get_styles_for_spot(spot_dict)
        if norm_style and norm_style not in styles:
            continue

        if city:
            spot_city = (spot_dict.get("city") or "").lower()
            if city.lower() not in spot_city:
                continue

        spot_dict["trip_styles"] = list(styles)
        results.append(spot_dict)

        if len(results) >= limit:
            break

    return json.dumps(results, ensure_ascii=False)


def _has_food_or_rest_feature(text: str) -> bool:
    """用關鍵字判斷景點是否偏向餐廳／美食或可當作休息點。"""
    if not text:
        return False
    return any(
        k in text
        for k in [
            "餐廳",
            "美食",
            "小吃",
            "夜市",
            "咖啡",
            "咖啡廳",
            "甜點",
            "早午餐",
            "休息",
            "休憩",
            "咖啡店",
        ]
    )


@mcp.tool(
    name="recommend_itinerary_candidates",
    description=(
        "行程候選景點推薦。輸入城市、天數、旅遊風格、鬆/緊湊節奏、是否包含餐廳/休息點，"
        "回傳一組適合拿去排 daily itinerary 的候選景點列表。"
    ),
)
async def recommend_itinerary_candidates(
    city: str,
    days: int = 3,
    trip_style: str | None = None,
    pace: str = "normal",
    include_food_and_rest: bool = True,
) -> str:
    """
    產生排程前的「候選景點」清單。
    - 先根據城市過濾，再依人氣與旅遊風格排序。
    - pace: 'loose'/'normal'/'tight'，影響每一天預估景點數量。
    - include_food_and_rest: True 時，適度混入帶有餐飲或可休息特性的點。
    回傳格式：list[dict]，每個 dict 會帶有 score、trip_styles 等欄位，方便 LLM 後處理。
    """
    raw_spots = await get_spots(top_n=800)

    days = max(1, _safe_int(days, 3))
    pace_norm = (pace or "normal").lower()
    if "loose" in pace_norm or "chill" in pace_norm or "輕鬆" in pace_norm:
        spots_per_day = 4
    elif "tight" in pace_norm or "busy" in pace_norm or "緊湊" in pace_norm:
        spots_per_day = 6
    else:
        spots_per_day = 5

    target_count = days * spots_per_day

    city_lower = (city or "").lower()
    style_norm = (trip_style or "").strip()

    scored: list[dict] = []
    for spot in raw_spots:
        base = {
            "spot_id": getattr(spot, "spot_id", None),
            "name": getattr(spot, "name", None),
            "description": getattr(spot, "description", None),
            "popularity": getattr(spot, "popularity", 0),
            "is_active": getattr(spot, "is_active", None),
            "city": getattr(spot, "city", None),
            "category": getattr(spot, "category", None),
        }

        # 以城市過濾（必要條件），若完全對不到再由 LLM 自行補救
        if city_lower:
            spot_city = (base.get("city") or "").lower()
            if city_lower not in spot_city:
                continue

        styles = _get_styles_for_spot(base)
        text = _extract_text_fields(base)

        score = _safe_get_popularity({"popularity": base.get("popularity", 0)})

        # 風格加權：符合指定旅遊風格就給額外分數
        if style_norm and style_norm in styles:
            score += 5000

        # 食物 / 休息點加權
        has_food_or_rest = _has_food_or_rest_feature(text)
        if include_food_and_rest and has_food_or_rest:
            score += 2000

        base["trip_styles"] = list(styles)
        base["score"] = score
        base["has_food_or_rest"] = has_food_or_rest
        scored.append(base)

    # 依分數排序
    scored.sort(key=lambda s: s.get("score", 0), reverse=True)

    # 取前 N 筆作為候選
    candidates = scored[: max(target_count, 1)]

    payload = {
        "city": city,
        "days": days,
        "trip_style": trip_style,
        "pace": pace,
        "include_food_and_rest": include_food_and_rest,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    return json.dumps(payload, ensure_ascii=False)

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

@mcp.tool(
    name="ping",
    description="ping:。"
)
async def ping(text: str | None = None) -> str:
    return json.dumps(
        {"ok": True, "reply": "pong", "echo": text},
        ensure_ascii=False
    )

async def main():
    # Use run_async() in async contexts
    await mcp.run_async(transport="http", port=8000)

if __name__ == "__main__":
    asyncio.run(main())