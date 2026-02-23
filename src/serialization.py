import json
from util.logging_decorator import log_calls

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