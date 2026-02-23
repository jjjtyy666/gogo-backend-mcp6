import asyncio
import pytest


def test_trip_import_does_not_start_event_loop():
    # Importing the module should be side-effect free (no asyncio.run, no server start).
    import trip  # noqa: F401


@pytest.mark.asyncio
async def test_trip_main_inside_running_loop_does_not_raise(monkeypatch):
    import trip

    called = {"async": 0, "sync": 0}

    async def fake_run_stdio_async():
        called["async"] += 1

    def fake_run(*args, **kwargs):
        called["sync"] += 1

    monkeypatch.setattr(trip.mcp, "run_stdio_async", fake_run_stdio_async)
    monkeypatch.setattr(trip.mcp, "run", fake_run)

    # We're already in a running loop because of pytest.mark.asyncio
    trip.main()

    # The task should have been scheduled on the running loop.
    await asyncio.sleep(0)

    assert called["sync"] == 0
    assert called["async"] == 1


@pytest.mark.asyncio
async def test_tools_await_actions_and_serialize(monkeypatch):
    import trip

    class DummySpot:
        def __init__(self, spot_id: int, name: str, popularity: int, is_active: bool = True):
            self.spot_id = spot_id
            self.name = name
            self.description = None
            self.popularity = popularity
            self.is_active = is_active

    async def fake_get_main_spots():
        return [DummySpot(1, "A", 4000)]

    async def fake_get_sub_spots():
        return [DummySpot(2, "B", 2000)]

    async def fake_get_spots():
        return [DummySpot(3, "C", 9999)]

    monkeypatch.setattr(trip, "get_main_spots", fake_get_main_spots)
    monkeypatch.setattr(trip, "get_sub_spots", fake_get_sub_spots)
    monkeypatch.setattr(trip, "get_spots", fake_get_spots)

    out1 = await trip.major_views()
    out2 = await trip.sub_views()
    out3 = await trip.get_top_10()

    assert '"spot_id": 1' in out1
    assert '"spot_id": 2' in out2
    assert '"spot_id": 3' in out3
