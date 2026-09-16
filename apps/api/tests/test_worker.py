from app import worker


def test_worker_persists_available_basin_context(monkeypatch):
    events = []
    monkeypatch.setattr(worker, "claim_next", lambda: {"id": "job-id", "latitude": 13.0, "longitude": 80.0, "radius_km": 2})
    monkeypatch.setattr(worker, "fetch_open_meteo", lambda *_: {"timezone": "GMT", "hourly": {"time": ["2026-01-01T00:00"], "precipitation": [0.0]}})
    monkeypatch.setattr(worker, "save_weather", lambda *args: events.append(("weather", args)))
    monkeypatch.setattr(worker, "save_rainfall_context", lambda *args: events.append(("rain", args)))
    monkeypatch.setattr(worker, "get_basin_context", lambda *_: {"status": "available", "basin_id": 123})
    monkeypatch.setattr(worker, "save_basin_context", lambda *args: events.append(("basin", args)))
    monkeypatch.setattr(worker, "evaluate_terrain", lambda *_: {"status": "available", "score": 61})
    monkeypatch.setattr(worker, "save_terrain_assessment", lambda *args: events.append(("terrain", args)))
    monkeypatch.setattr(worker, "transition", lambda *args: events.append(("transition", args)))

    assert worker.process_one() is True
    assert [event[0] for event in events] == ["weather", "rain", "basin", "terrain", "transition"]
    assert events[-1][1][2] == worker.AnalysisStatus.COMPLETE


def test_worker_waits_when_terrain_is_missing(monkeypatch):
    events = []
    monkeypatch.setattr(worker, "claim_next", lambda: {"id": "job-id", "latitude": 13.0, "longitude": 80.0, "radius_km": 2})
    monkeypatch.setattr(worker, "fetch_open_meteo", lambda *_: {"timezone": "GMT", "hourly": {"time": ["2026-01-01T00:00"], "precipitation": [1.0]}})
    monkeypatch.setattr(worker, "save_weather", lambda *args: events.append(("weather", args)))
    monkeypatch.setattr(worker, "save_rainfall_context", lambda *args: events.append(("rain", args)))
    monkeypatch.setattr(worker, "get_basin_context", lambda *_: {"status": "available", "basin_id": 123})
    monkeypatch.setattr(worker, "save_basin_context", lambda *args: events.append(("basin", args)))
    monkeypatch.setattr(worker, "evaluate_terrain", lambda *_: {"status": "unavailable", "missing_datasets": ["fabdem"]})
    monkeypatch.setattr(worker, "save_terrain_assessment", lambda *args: events.append(("terrain", args)))
    monkeypatch.setattr(worker, "transition", lambda *args: events.append(("transition", args)))

    assert worker.process_one() is True
    assert events[-1][1][2] == worker.AnalysisStatus.WAITING_FOR_DATA
    assert "FABDEM" in events[-1][1][4]


def test_worker_does_not_fail_job_when_terrain_raises(monkeypatch):
    events = []
    monkeypatch.setattr(worker, "claim_next", lambda: {"id": "job-id", "latitude": 13.0, "longitude": 80.0, "radius_km": 2})
    monkeypatch.setattr(worker, "fetch_open_meteo", lambda *_: {"timezone": "GMT", "hourly": {"time": ["2026-01-01T00:00"], "precipitation": [1.0]}})
    monkeypatch.setattr(worker, "save_weather", lambda *args: events.append(("weather", args)))
    monkeypatch.setattr(worker, "save_rainfall_context", lambda *args: events.append(("rain", args)))
    monkeypatch.setattr(worker, "get_basin_context", lambda *_: {"status": "available", "basin_id": 123})
    monkeypatch.setattr(worker, "save_basin_context", lambda *args: events.append(("basin", args)))
    monkeypatch.setattr(worker, "evaluate_terrain", lambda *_: (_ for _ in ()).throw(RuntimeError("raster failed")))
    monkeypatch.setattr(worker, "save_terrain_assessment", lambda *args: events.append(("terrain", args)))
    monkeypatch.setattr(worker, "transition", lambda *args: events.append(("transition", args)))

    assert worker.process_one() is True
    assert events[-1][1][2] == worker.AnalysisStatus.WAITING_FOR_DATA
    assert events[-2][1][1]["status"] == "unavailable"


def test_worker_does_nothing_when_queue_is_empty(monkeypatch):
    monkeypatch.setattr(worker, "claim_next", lambda: None)
    assert worker.process_one() is False
