import asyncio
from datetime import date
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.store import DocumentStore
from app.weather import WeatherClient


def weather_fixture(params):
    start, end = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
    days = (end - start).days + 1
    from datetime import timedelta
    dates = [(start + timedelta(days=index)).isoformat() for index in range(days)]
    values = [30 if "2021-06-01" <= day <= "2021-06-03" else 20 for day in dates]
    return {"latitude": 28.6, "longitude": 77.2, "timezone": "Asia/Kolkata", "utc_offset_seconds": 19800,
            "daily_units": {"time": "iso8601", "temperature_2m_max": "°C"},
            "daily": {"time": dates, "temperature_2m_max": values}}


@pytest.fixture
def client(tmp_path):
    calls = []
    def transport(request):
        assert request.url.host == "archive-api.open-meteo.com"
        params = dict(request.url.params)
        calls.append(params)
        return httpx.Response(200, json=weather_fixture(params))
    app = create_app(tmp_path / "weather.json", transport=httpx.MockTransport(transport))
    with TestClient(app) as test_client:
        yield test_client, calls


def query(**changes):
    return {"latitude": 28.6, "longitude": 77.2, "start_year": 2021, "end_year": 2021, **changes}


def test_cache_survives_database_reopen_and_expires(tmp_path):
    path = tmp_path / "data.json"
    store = DocumentStore(path)
    store.put("analyses", "a", {"events": 3}, ttl=60)
    store.close()
    store = DocumentStore(path)
    assert store.get("analyses", "a")["data"] == {"events": 3}
    store.put("analyses", "expired", {"events": 4}, ttl=-1)
    assert store.get("analyses", "expired") is None
    store.close()


def test_api_reads_persisted_summary_before_fetching(client):
    api, calls = client
    first = api.post("/api/analyze", json=query())
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["summary"]["total_events"] == 1
    assert body["cache"]["analysis_hit"] is False
    second = api.post("/api/analyze", json=query())
    assert second.status_code == 200
    assert second.json()["cache"]["analysis_hit"] is True
    assert len(calls) == 1
    assert calls[0]["models"] == "era5"
    assert calls[0]["temperature_unit"] == "celsius"
    assert calls[0]["start_date"] == "1991-01-01"
    assert calls[0]["end_date"] == "2021-12-31"


@pytest.mark.parametrize("changes", [
    {"latitude": 91}, {"longitude": -181}, {"latitude": "NaN"},
    {"start_year": 1939}, {"start_year": 2022, "end_year": 2021},
    {"end_year": date.today().year}, {"hazard": "drought"}, {"unexpected": "x"},
])
def test_unsafe_or_unsupported_inputs_are_rejected(client, changes):
    api, calls = client
    assert api.post("/api/analyze", json=query(**changes)).status_code == 422
    assert calls == []


def test_health_is_available_without_upstream_calls(client):
    api, calls = client
    assert api.get("/api/health").json()["status"] == "ok"
    assert calls == []


def test_rate_limit_stops_requests_and_returns_retry_after(client):
    api, _ = client
    for _ in range(10):
        assert api.post("/api/analyze", json=query()).status_code == 200
    response = api.post("/api/analyze", json=query())
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1


@pytest.mark.parametrize("status,expected", [(429, 503), (500, 502), (302, 502)])
def test_upstream_failure_is_sanitized_and_not_cached(tmp_path, status, expected):
    def transport(request):
        return httpx.Response(status, text="provider-private-debug-details", headers={"Location": "http://localhost/"})
    app = create_app(tmp_path / "weather.json", transport=httpx.MockTransport(transport))
    with TestClient(app) as api:
        response = api.post("/api/analyze", json=query())
        assert response.status_code == expected
        assert "provider-private-debug-details" not in response.text
        assert app.state.store.get("analyses", "28.6000:77.2000:2021:2021:v1") is None


def test_upstream_timeout_returns_gateway_timeout(tmp_path):
    def transport(request):
        raise httpx.ReadTimeout("timeout", request=request)
    app = create_app(tmp_path / "weather.json", transport=httpx.MockTransport(transport))
    with TestClient(app) as api:
        assert api.post("/api/analyze", json=query()).status_code == 504


def test_malformed_response_is_rejected(tmp_path):
    app = create_app(tmp_path / "weather.json", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"daily": {}})))
    with TestClient(app) as api:
        assert api.post("/api/analyze", json=query()).status_code == 502


def test_cache_is_shared_after_application_restart(tmp_path):
    path = tmp_path / "weather.json"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=weather_fixture(dict(request.url.params))))
    with TestClient(create_app(path, transport=transport)) as api:
        assert api.post("/api/analyze", json=query()).status_code == 200
    def fail_if_called(request):
        raise AssertionError("Cached results should not call the weather provider")
    with TestClient(create_app(path, transport=httpx.MockTransport(fail_if_called))) as api:
        response = api.post("/api/analyze", json=query())
        assert response.status_code == 200
        assert response.json()["cache"]["analysis_hit"] is True


@pytest.mark.parametrize("path", ["/docs", "/docs/oauth2-redirect", "/redoc"])
def test_documentation_resources_are_allowed_by_scoped_csp(client, path):
    api, calls = client
    response = api.get(path)
    assert response.status_code == 200
    policy = dict(directive.strip().split(" ", 1) for directive in response.headers["Content-Security-Policy"].split(";") if directive.strip())
    assert "https://cdn.jsdelivr.net" in policy["script-src"].split()
    assert "'unsafe-inline'" in policy["script-src"].split()
    assert "https://cdn.jsdelivr.net" in policy["style-src"].split()
    assert policy["connect-src"] == "'self'"
    assert policy["object-src"] == "'none'"
    assert policy["frame-ancestors"] == "'none'"
    if path == "/docs":
        assert "SwaggerUIBundle({" in response.text
    if path == "/redoc":
        assert "https://fonts.googleapis.com" in policy["style-src"].split()
        assert "https://fonts.gstatic.com" in policy["font-src"].split()
    assert calls == []


@pytest.mark.parametrize("path", ["/api/health", "/openapi.json", "/", "/docs/not-a-doc-page"])
def test_documentation_script_permissions_do_not_reach_app_or_api(client, path):
    api, calls = client
    response = api.get(path)
    policy = response.headers["Content-Security-Policy"]
    script_policy = next(directive.strip() for directive in policy.split(";") if directive.strip().startswith("script-src "))
    assert script_policy == "script-src 'self'"
    assert "https://cdn.jsdelivr.net" not in policy
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert calls == []
