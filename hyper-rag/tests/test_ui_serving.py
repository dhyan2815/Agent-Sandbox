"""Which page `/` serves: the built React app when it exists, the classic page otherwise."""

import pytest
from fastapi.testclient import TestClient

from hyper_rag import api


@pytest.fixture
def make_client(settings):
    original = api.get_settings

    def make(ui_dir) -> TestClient:
        configured = settings.model_copy(update={"ui_dir": ui_dir})
        api.get_settings = lambda: configured
        return TestClient(api.app)

    yield make
    api.get_settings = original


@pytest.fixture
def built(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div><script src="/assets/app-1a2b.js">')
    (dist / "assets" / "app-1a2b.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("not for you")
    return dist


def test_serves_the_classic_page_until_the_app_is_built(make_client, tmp_path):
    client = make_client(tmp_path / "missing")
    page = client.get("/")
    assert page.status_code == 200 and 'id="ask-form"' in page.text


def test_serves_the_built_app_and_its_assets(make_client, built):
    client = make_client(built)
    assert 'id="root"' in client.get("/").text
    script = client.get("/assets/app-1a2b.js")
    assert script.status_code == 200 and "immutable" in script.headers["cache-control"]
    assert 'id="ask-form"' in client.get("/classic").text  # still reachable


@pytest.mark.parametrize("name", ["missing.js", "..%2Fsecret.txt", "%2e%2e%2Fsecret.txt"])
def test_assets_cannot_reach_outside_their_folder(make_client, built, name):
    assert make_client(built).get(f"/assets/{name}").status_code == 404


@pytest.mark.parametrize("name", ["..", "../secret.txt", "../dist/index.html"])
def test_asset_route_refuses_names_that_climb(make_client, built, name):
    # An HTTP client normalises "/assets/.." away, so call the route as a server could see it.
    make_client(built)
    with pytest.raises(api.HTTPException) as refused:
        api.asset(name)
    assert refused.value.status_code == 404
