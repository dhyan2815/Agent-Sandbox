"""Single-user login (plan v2, phase 0): off without a password, required with one."""

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api, auth

PASSWORD = "correct horse battery"


@pytest.fixture
def make_client(settings, store):
    originals = api.get_settings, api.get_store

    def make(password: str) -> TestClient:
        configured = settings.model_copy(update={"password": password})
        api.get_settings, api.get_store = (lambda: configured), (lambda: store)
        return TestClient(api.app)

    auth.limiter._failures.clear()
    api.get_jobs.cache_clear()
    yield make
    api.get_settings, api.get_store = originals
    auth.limiter._failures.clear()
    api.get_jobs.cache_clear()


def test_without_a_password_nothing_changes(make_client):
    client = make_client("")
    assert client.get("/collections").status_code == 200
    assert client.get("/config").json()["login"] is False
    assert client.get("/login", follow_redirects=False).headers["location"] == "/"


def test_with_a_password_the_api_refuses_and_pages_redirect(make_client):
    client = make_client(PASSWORD)
    assert client.get("/collections").status_code == 401
    assert client.post("/collections", json={"name": "x"}).status_code == 401
    page = client.get("/", headers={"accept": "text/html"}, follow_redirects=False)
    assert page.status_code == 303 and page.headers["location"] == "/login"
    assert client.get("/health").status_code == 200  # the host's probe stays open
    login = client.get("/login")
    assert login.status_code == 200 and 'type="password"' in login.text


def test_logging_in_sets_a_cookie_that_opens_the_app(make_client):
    client = make_client(PASSWORD)
    response = client.post("/login", data={"password": PASSWORD}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert auth.COOKIE in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert "Secure" not in cookie  # plain HTTP here; set over HTTPS
    assert client.get("/collections").status_code == 200
    assert client.get("/config").json()["login"] is True

    client.post("/logout")
    assert client.get("/collections").status_code == 401


def test_cookie_is_secure_behind_an_https_proxy(make_client):
    client = make_client(PASSWORD)
    response = client.post(
        "/login",
        data={"password": PASSWORD},
        headers={"x-forwarded-proto": "https"},
        follow_redirects=False,
    )
    assert "Secure" in response.headers["set-cookie"]


def test_wrong_password_is_refused_then_rate_limited(make_client):
    client = make_client(PASSWORD)
    for _ in range(auth.MAX_FAILURES):
        wrong = client.post("/login", data={"password": "nope"}, follow_redirects=False)
        assert wrong.status_code == 401 and "not right" in wrong.text
    # Even the right password waits now: guessing must not be able to continue.
    blocked = client.post("/login", data={"password": PASSWORD}, follow_redirects=False)
    assert blocked.status_code == 429
    assert client.get("/collections").status_code == 401


def test_tokens_are_signed_expire_and_follow_the_password():
    token = auth.make_token(PASSWORD, days=1, now=1000)
    assert auth.valid_token(PASSWORD, token, now=1001)
    assert not auth.valid_token(PASSWORD, token, now=1000 + 86400 + 1)  # expired
    assert not auth.valid_token("a new password", token, now=1001)  # password changed
    expiry, signature = token.split(".")
    assert not auth.valid_token(PASSWORD, f"{int(expiry) + 999}.{signature}", now=1001)
    for junk in (None, "", "abc", "1.2.3", "x.y"):
        assert not auth.valid_token(PASSWORD, junk)


def test_a_forged_cookie_is_refused(make_client):
    client = make_client(PASSWORD)
    client.cookies.set(auth.COOKIE, auth.make_token("guessed", days=1))
    assert client.get("/collections").status_code == 401
