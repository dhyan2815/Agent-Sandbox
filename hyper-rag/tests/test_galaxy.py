"""Plan v2 phase 4 (side branch): the Galaxy layout."""

import numpy as np
from fastapi.testclient import TestClient

from hyper_rag import api
from hyper_rag.projection import fit


def test_pca_keeps_the_main_directions_and_places_new_points_alike():
    rng = np.random.default_rng(1)
    # Two clusters far apart along one direction: PCA's first axis must separate them.
    base = rng.normal(size=(1, 32))
    a = rng.normal(scale=0.1, size=(50, 32)) + base
    b = rng.normal(scale=0.1, size=(50, 32)) - base
    matrix = np.vstack([a, b]).astype(np.float32)
    projection = fit(matrix)
    xyz = projection.place(matrix)
    assert np.sign(xyz[:50, 0]).std() == 0 and np.sign(xyz[50:, 0]).std() == 0
    assert np.sign(xyz[0, 0]) != np.sign(xyz[50, 0])
    assert projection.explained[0] > 0.8
    # A new point near cluster a lands on a's side.
    assert np.sign(projection.place(base[0] * 1.0)[0, 0]) == np.sign(xyz[0, 0])
    assert np.percentile(np.linalg.norm(xyz, axis=1), 98) <= 1.0001


def test_the_map_endpoint_and_question_position(settings, solar):
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: settings), (lambda: solar)
    api.get_llms.cache_clear()
    try:
        client = TestClient(api.app)
        body = client.get("/collections/solar-docs/map").json()
        assert len(body["points"]) == len(solar.retriever("solar-docs").chunks)
        assert {p["file_id"] for p in body["points"]} <= {f["id"] for f in body["files"]}
        assert all(len(p["xyz"]) == 3 for p in body["points"]) and "projection" not in body
        answer = client.post(
            "/collections/solar-docs/ask", json={"question": "What is the inverter warranty?"}
        ).json()
        run = client.get(f"/collections/solar-docs/runs/{answer['run_id']}").json()
        position = next(e for e in run["events"] if e["t"] == "q.position")
        assert len(position["xyz"]) == 3
        assert client.get("/collections/nope/map").status_code == 404
    finally:
        api.get_settings, api.get_store = originals
        api.get_llms.cache_clear()
