"""Single-user login: one password, a signed session cookie.

Off unless HYPER_RAG_PASSWORD is set, so running on your own machine and the tests work
as before. Set it before the app is reachable by anyone else (plan v2: hosting needs it).

    GET  /login    the login form
    POST /login    check the password, set the cookie, go to the app
    POST /logout   clear the cookie

The cookie is "<expiry>.<hmac>". The signing key is derived from the password, so
changing the password logs every browser out, and there is no second secret to manage.
HttpOnly keeps scripts from reading it, SameSite=Lax keeps other sites from sending it
with their form posts (the CSRF case for a cookie session), and Secure is set when the
request arrived over HTTPS.

Wrong passwords are limited per client address: after MAX_FAILURES in FAILURE_WINDOW
seconds that address gets 429 until the window passes.
"""

import hashlib
import hmac
import html
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

COOKIE = "hyper_rag_session"
MAX_FAILURES = 5
FAILURE_WINDOW = 15 * 60
# Reachable without a session: the login itself, and the host's health probe.
OPEN_PATHS = {"/login", "/logout", "/health"}


def _key(password: str) -> bytes:
    return hashlib.sha256(b"hyper-rag session v1\x00" + password.encode("utf-8")).digest()


def make_token(password: str, days: int, now: float | None = None) -> str:
    expiry = int((now if now is not None else time.time()) + days * 86400)
    signature = hmac.new(_key(password), str(expiry).encode(), hashlib.sha256).hexdigest()
    return f"{expiry}.{signature}"


def valid_token(password: str, token: str | None, now: float | None = None) -> bool:
    if not token or token.count(".") != 1:
        return False
    expiry, signature = token.split(".")
    if not expiry.isdigit():
        return False
    expected = hmac.new(_key(password), expiry.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    return int(expiry) > (now if now is not None else time.time())


class FailureLimiter:
    def __init__(self, max_failures: int = MAX_FAILURES, window: float = FAILURE_WINDOW):
        self.max_failures = max_failures
        self.window = window
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, client: str, now: float) -> deque[float]:
        failures = self._failures[client]
        while failures and failures[0] <= now - self.window:
            failures.popleft()
        return failures

    def blocked(self, client: str) -> bool:
        with self._lock:
            return len(self._recent(client, time.monotonic())) >= self.max_failures

    def fail(self, client: str) -> None:
        with self._lock:
            self._recent(client, time.monotonic()).append(time.monotonic())

    def clear(self, client: str) -> None:
        with self._lock:
            self._failures.pop(client, None)


limiter = FailureLimiter()


def _is_https(request: Request) -> bool:
    # Behind a host's proxy (Hugging Face, Render) the app sees plain HTTP; the proxy says
    # what the browser used. Run uvicorn with --proxy-headers so request.url agrees too.
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return request.url.scheme == "https" or forwarded == "https"


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


client_address = _client  # public name: the quota guard keys on the same address


def _wants_page(request: Request) -> bool:
    return request.method == "GET" and "text/html" in request.headers.get("accept", "")


def require_login(request: Request, password: str) -> Response | None:
    """None if the request may go ahead; otherwise the response that sends it to log in."""
    if not password or request.url.path in OPEN_PATHS:
        return None
    if valid_token(password, request.cookies.get(COOKIE)):
        return None
    if _wants_page(request):
        return RedirectResponse("/login", status_code=303)
    return JSONResponse({"detail": "Log in first."}, status_code=401)


def login_page(error: str = "", status_code: int = 200) -> HTMLResponse:
    message = f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ""
    return HTMLResponse(_PAGE.replace("{message}", message), status_code=status_code)


def login(request: Request, password: str, submitted: str, days: int) -> Response:
    client = _client(request)
    if limiter.blocked(client):
        return login_page("Too many wrong passwords. Try again in 15 minutes.", 429)
    if not password:
        return RedirectResponse("/", status_code=303)  # login is off: nothing to check
    if not hmac.compare_digest(submitted.encode("utf-8"), password.encode("utf-8")):
        limiter.fail(client)
        return login_page("That password is not right.", 401)
    limiter.clear(client)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE,
        make_token(password, days),
        max_age=days * 86400,
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
        path="/",
    )
    return response


def logout() -> Response:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE, path="/")
    return response


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hyper-RAG · Log in</title>
<style>
  :root { --bg: #f7f7f5; --card: #fff; --text: #1d1d1b; --muted: #6b6b66; --line: #e2e2dc;
          --accent: #2f6f4f; --error: #a3312a; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #161615; --card: #1f1f1d; --text: #ececea; --muted: #a3a39c; --line: #34342f;
            --accent: #6fbf94; --error: #f08a80; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px;
         background: var(--bg); color: var(--text);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  form { width: 100%; max-width: 340px; background: var(--card); border: 1px solid var(--line);
         border-radius: 10px; padding: 28px; }
  h1 { font-size: 1.2rem; margin: 0 0 4px; }
  p { margin: 0 0 18px; color: var(--muted); }
  label { display: block; font-weight: 600; margin-bottom: 6px; }
  input { width: 100%; padding: 9px 11px; border: 1px solid var(--line); border-radius: 7px;
          background: var(--bg); color: var(--text); font: inherit; }
  input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
  button { margin-top: 16px; width: 100%; padding: 9px; border: 0; border-radius: 7px;
           background: var(--accent); color: #fff; font: inherit; font-weight: 600;
           cursor: pointer; }
  .error { color: var(--error); margin: 12px 0 0; }
</style>
</head>
<body>
<form method="post" action="/login">
  <h1>Hyper-RAG</h1>
  <p>This app is private. Enter its password.</p>
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password"
         required autofocus>
  <button type="submit">Log in</button>
  {message}
</form>
</body>
</html>
"""
