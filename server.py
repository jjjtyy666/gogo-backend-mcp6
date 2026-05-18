from fastmcp import FastMCP
import asyncio, json, os
from src.action import get_sub_spots, get_main_spots, get_spots, get_spots_filtered
from src.serialization import serialize_spots, spot_to_dict

mcp = FastMCP(name="trip")

# 與聊天 prompt 一致：喜歡／不喜歡風格枚舉
VALID_TRIP_STYLES = frozenset(
    {
        "自然戶外",
        "文化歷史",
        "美食餐飲",
        "放鬆療癒",
        "藝文展覽",
        "熱門打卡",
        "逛街購物",
        "夜生活",
        "親子休閒",
    }
)

VALID_TRAVELER_PROFILES = frozenset(
    {
        "打卡狂熱者",
        "購物達人",
        "美食探索者",
        "戶外踏青派",
        "文藝展覽愛好者",
    }
)


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


def _normalize_label_list(items: list[str] | None, valid: frozenset[str], max_n: int) -> list[str]:
    """去空白、去重（保序）、只保留合法標籤，最多 max_n 個。"""
    if not items:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for x in items:
        if not isinstance(x, str):
            continue
        s = x.strip()
        if not s or s not in valid or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= max_n:
            break
    return out


def _merge_trip_styles(
    trip_styles: list[str] | None,
    trip_style: str | None,
    max_n: int = 3,
) -> list[str]:
    """合併 list 與舊版單一字串參數，統一為最多三個合法風格。"""
    merged: list[str] = []
    seen: set[str] = set()
    for src in (trip_styles or []):
        if isinstance(src, str):
            s = src.strip()
            if s in VALID_TRIP_STYLES and s not in seen:
                seen.add(s)
                merged.append(s)
        if len(merged) >= max_n:
            return merged
    if trip_style and isinstance(trip_style, str):
        s = trip_style.strip()
        if s in VALID_TRIP_STYLES and s not in seen:
            merged.append(s)
    return merged[:max_n]


def _get_styles_for_spot(spot: dict) -> set[str]:
    """
    依據 name/description/category 關鍵字，推估景點適合的旅遊風格（與 prompt 九宮格一致）。
    """
    text = _extract_text_fields(spot)
    tl = text.lower()
    styles: set[str] = set()

    if any(k in text for k in ["山", "森林", "步道", "國家公園", "海", "海灘", "沙灘", "湖", "溪谷", "瀑布", "戶外", "健行", "登山", "草原", "自然", "生態", "露營"]):
        styles.add("自然戶外")

    if any(k in text for k in ["古蹟", "歷史", "文化", "老街", "古城", "老城", "廟", "寺", "祠", "遺址", "城門", "紀念館"]):
        styles.add("文化歷史")

    if any(k in text for k in ["美食", "小吃", "夜市", "餐廳", "市場", "點心", "甜點", "咖啡", "早午餐", "料理", "吃到飽", "餐飲"]):
        styles.add("美食餐飲")

    if any(k in tl for k in ["溫泉", "spa", "按摩", "療癒", "足湯", "湯屋", "養生", "度假村", "桑拿"]):
        styles.add("放鬆療癒")

    if any(k in text for k in ["展覽", "美術館", "藝廊", "文創", "表演", "劇場", "音樂廳", "書店", "藝術", "博物館"]):
        styles.add("藝文展覽")

    if any(k in text for k in ["網美", "打卡", "拍照", "景觀台", "觀景台", "裝置藝術", "彩虹"]) or "ig" in tl:
        styles.add("熱門打卡")

    if any(k in tl for k in ["購物", "百貨", "商場", "outlet", "商圈", "免稅", "購物中心"]):
        styles.add("逛街購物")

    if any(k in text for k in ["酒吧", "夜店", "駐唱", "宵夜", "夜遊", "夜景", "啤酒", "夜生活"]):
        styles.add("夜生活")

    if any(k in text for k in ["親子", "動物園", "樂園", "遊樂", "兒童", "小朋友", "水族館", "農場", "親子館"]):
        styles.add("親子休閒")

    return styles


def _traveler_profile_bonus(profiles: set[str], styles: set[str]) -> int:
    """依旅行者類型（最多三種）對符合的風格加分。"""
    b = 0
    if "打卡狂熱者" in profiles:
        if "熱門打卡" in styles:
            b += 3000
        if "藝文展覽" in styles:
            b += 1500
    if "購物達人" in profiles and "逛街購物" in styles:
        b += 3000
    if "美食探索者" in profiles and "美食餐飲" in styles:
        b += 3000
    if "戶外踏青派" in profiles and "自然戶外" in styles:
        b += 3000
    if "文藝展覽愛好者" in profiles:
        if "藝文展覽" in styles:
            b += 3000
        if "文化歷史" in styles:
            b += 1500
    return b



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
        "依旅遊風格推薦景點。風格須為：自然戶外、文化歷史、美食餐飲、放鬆療癒、藝文展覽、"
        "熱門打卡、逛街購物、夜生活、親子休閒；trip_styles 最多 3 個（與使用者 prompt 一致）。"
        "可選 city（資料庫 ILIKE 篩選）、limit。若未傳風格則依城市／人氣回傳。"
        "相容參數 trip_style：單一風格字串，會與 trip_styles 合併後最多取 3 個。"
    ),
)
async def get_spots_by_trip_style(
    trip_styles: list[str] | None = None,
    trip_style: str | None = None,
    city: str | None = None,
    limit: int = 20,
) -> str:
    """
    依啟發式標籤過濾；資料來自 get_spots_filtered（先依城市在 DB 篩選，再依人氣排序）。
    若合併後仍無合法風格，則不過濾風格，只回傳該城市（或全庫）高人氣景點。
    """
    wanted = _merge_trip_styles(trip_styles, trip_style, max_n=3)
    limit = max(1, min(100, _safe_int(limit, 20)))
    pool_limit = max(limit * 25, 400)
    data = await get_spots_filtered(city=city, limit=pool_limit)

    results: list[dict] = []
    for spot in data:
        spot_dict = spot_to_dict(spot)
        styles = _get_styles_for_spot(spot_dict)
        if wanted and not (styles & set(wanted)):
            continue
        spot_dict["trip_styles"] = sorted(styles)
        results.append(spot_dict)
        if len(results) >= limit:
            break

    if wanted and not results:
        for spot in data:
            spot_dict = spot_to_dict(spot)
            spot_dict["trip_styles"] = sorted(_get_styles_for_spot(spot_dict))
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
        "行程候選景點推薦。必填城市；preferred_styles／avoid_styles／traveler_profiles 各最多 3 個，"
        "風格枚舉與聊天 prompt 相同。pace 控制鬆緊；include_food_and_rest 會替餐飲／休息點加分。"
        "相容 trip_style：單一偏好風格，會併入 preferred_styles。"
    ),
)
async def recommend_itinerary_candidates(
    city: str,
    days: int = 3,
    preferred_styles: list[str] | None = None,
    avoid_styles: list[str] | None = None,
    traveler_profiles: list[str] | None = None,
    trip_style: str | None = None,
    pace: str = "normal",
    include_food_and_rest: bool = True,
) -> str:
    """
    先以 get_spots_filtered 在 DB 依城市與人氣取樣；排除 avoid_styles 命中者；
    preferred_styles 與 traveler_profiles 用於加權排序。
    """
    raw_spots = await get_spots_filtered(city=city, limit=1500)

    days = max(1, _safe_int(days, 3))
    pace_norm = (pace or "normal").lower()
    if "loose" in pace_norm or "chill" in pace_norm or "輕鬆" in pace_norm:
        spots_per_day = 4
    elif "tight" in pace_norm or "busy" in pace_norm or "緊湊" in pace_norm:
        spots_per_day = 6
    else:
        spots_per_day = 5

    target_count = days * spots_per_day

    preferred = _merge_trip_styles(preferred_styles, trip_style, max_n=3)
    avoid_set = set(_normalize_label_list(avoid_styles, VALID_TRIP_STYLES, max_n=3))
    profiles_set = set(_normalize_label_list(traveler_profiles, VALID_TRAVELER_PROFILES, max_n=3))

    scored: list[dict] = []
    for spot in raw_spots:
        base = spot_to_dict(spot)
        styles = _get_styles_for_spot(base)
        if avoid_set and (styles & avoid_set):
            continue

        text = _extract_text_fields(base)

        score = _safe_get_popularity({"popularity": base.get("popularity", 0)})

        pref_set = set(preferred)
        if pref_set:
            score += 5000 * len(styles & pref_set)

        score += _traveler_profile_bonus(profiles_set, styles)

        has_food_or_rest = _has_food_or_rest_feature(text)
        if include_food_and_rest and has_food_or_rest:
            score += 2000

        base["trip_styles"] = sorted(styles)
        base["score"] = score
        base["has_food_or_rest"] = has_food_or_rest
        scored.append(base)

    scored.sort(key=lambda s: s.get("score", 0), reverse=True)

    candidates = scored[: max(target_count, 1)]

    payload = {
        "city": city,
        "days": days,
        "preferred_styles": preferred,
        "avoid_styles": sorted(avoid_set),
        "traveler_profiles": sorted(profiles_set),
        "trip_style_legacy": trip_style,
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
    description="健康檢查；可選傳入 text 會在回傳 JSON 的 echo 欄位原樣帶回。",
)
async def ping(text: str | None = None) -> str:
    return json.dumps(
        {"ok": True, "reply": "pong", "echo": text},
        ensure_ascii=False
    )

async def main():
    port = int(os.environ.get("PORT", "8080"))
    await mcp.run_async(
        transport="http",
        host="0.0.0.0",
        port=port,
    )

if __name__ == "__main__":
    asyncio.run(main())