"""Plan v2 phase 6: warm-up, the quota guard, the settings check, readiness."""

import time

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api, deploy


@pytest.fixture
def client(settings, store):
    originals = api.get_settings, api.get_store
    api.get_settings, api.get_store = (lambda: settings), (lambda: store)
    for cached in (api.get_llms, api.get_jobs, api.get_quota, api.get_warmup):
        cached.cache_clear()
    yield TestClient(api.app)
    api.get_settings, api.get_store = originals
    for cached in (api.get_llms, api.get_jobs, api.get_quota, api.get_warmup):
        cached.cache_clear()


def test_warmup_reports_warming_then_ready():
    warmup = deploy.Warmup()
    assert warmup.state == "idle"
    warmup.start(lambda: time.sleep(0.05))
    assert warmup.state == "warming"
    warmup.wait(2)
    assert warmup.state == "ready" and warmup.to_dict()["seconds"] >= 0.05


def test_a_failed_warmup_is_reported_not_raised():
    def load():
        raise RuntimeError("model download blocked")

    warmup = deploy.Warmup()
    warmup.start(load)
    warmup.wait(2)
    assert warmup.state == "failed" and "model download blocked" in warmup.error


def test_quota_guard_limits_each_client_separately_and_recovers():
    guard = deploy.QuotaGuard(limit=2, window=0.2)
    assert guard.take("a") == 0 and guard.take("a") == 0
    assert guard.take("a") > 0  # third request inside the window
    assert guard.take("b") == 0  # another client is unaffected
    assert guard.left("a") == 0
    time.sleep(0.25)
    assert guard.take("a") == 0 and guard.left("a") == 1


def test_quota_guard_of_zero_is_off():
    guard = deploy.QuotaGuard(limit=0)
    assert all(guard.take("a") == 0 for _ in range(50)) and guard.left("a") is None


def test_health_is_open_and_reports_the_warm_state(client, settings, monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: settings.model_copy(update={"password": "pw"}))
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["warm"] in {"idle", "warming", "ready", "failed"}


def test_ready_probes_the_stores(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True and response.json()["checks"]["blobs"] == "ok"


def test_ready_is_503_when_a_store_fails(client, store, monkeypatch):
    def broken(prefix):
        raise ConnectionError("bucket unreachable")

    monkeypatch.setattr(store.blobs, "list", broken)
    response = client.get("/ready")
    assert response.status_code == 503
    assert "bucket unreachable" in response.json()["checks"]["blobs"]


def test_questions_over_the_hourly_budget_get_429(client, settings, monkeypatch):
    limited = settings.model_copy(update={"model_requests_per_hour": 2})
    monkeypatch.setattr(api, "get_settings", lambda: limited)
    api.get_quota.cache_clear()
    client.post("/collections", json={"name": "Solar"})
    path = "/collections/solar/ask"
    body = {"question": "How long does installation take?"}
    codes = [client.post(path, json=body).status_code for _ in range(3)]
    assert codes[2] == 429  # the first two were counted (400: nothing uploaded yet)
    refused = client.post(path, json=body)
    assert "Retry-After" in refused.headers and "Hourly limit" in refused.json()["detail"]


def test_settings_check_finds_what_a_host_needs(settings, monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    off = settings.offline()
    messages = {p.message for p in deploy.check_settings(off, hosted=True)}
    assert any("HYPER_RAG_PASSWORD" in m for m in messages)
    assert any("wiped on restart" in m for m in messages)
    ready = off.model_copy(update={"password": "pw", "blob_store": "s3", "s3_bucket": "b"})
    problems = deploy.check_settings(ready, hosted=True)
    assert any("AWS_ACCESS_KEY_ID" in p.message and p.level == "error" for p in problems)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    bucket = off.model_copy(update={"password": "pw", "blob_store": "hf", "hf_bucket": "me/b"})
    assert any("HF_TOKEN" in p.message for p in deploy.check_settings(bucket, hosted=True))
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    assert not [p for p in deploy.check_settings(bucket, hosted=True) if p.level == "error"]


def test_settings_check_needs_the_key_of_the_chosen_provider(settings):
    groq = settings.model_copy(update={"llm_provider": "groq", "groq_api_key": ""})
    assert any(
        p.level == "error" and "GROQ_API_KEY" in p.message for p in deploy.check_settings(groq)
    )
    keyed = groq.model_copy(update={"groq_api_key": "k"})
    assert not any(p.level == "error" for p in deploy.check_settings(keyed, hosted=False))
