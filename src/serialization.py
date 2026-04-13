import json
from util.logging_decorator import log_calls


def spot_to_dict(spot) -> dict:
    """將 Spot ORM 轉成 API 常用欄位（含城市／類別，供風格與行程工具一致使用）。"""
    return {
        "spot_id": spot.spot_id,
        "name": spot.name,
        "description": spot.description,
        "popularity": spot.popularity,
        "is_active": spot.is_active,
        "city": getattr(spot, "city", None),
        "category": getattr(spot, "category", None),
    }


@log_calls()
def serialize_spots(spots):
    """Serialize a list of Spot objects into a list of dictionaries."""
    serialized = []
    for spot in spots:
        serialized.append({
            "spot_id": spot.spot_id,
            "name": spot.name,
            "description": spot.description,
            "popularity": spot.popularity,
            "is_active": spot.is_active,
        })
    return json.dumps(serialized, ensure_ascii=False)