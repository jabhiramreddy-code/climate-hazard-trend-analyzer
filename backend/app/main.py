import asyncio
from collections import deque
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import logging
import math
import os
from pathlib import Path
from time import monotonic
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.analysis import analyze
from app.models import AnalysisRequest
from app.store import DocumentStore
from app.weather import WeatherClient

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


class RateLimiter:
    def __init__(self):
        self.clients = {}

    def check(self, address):
        now = monotonic()
        self.clients = {key: times for key, times in self.clients.items() if times and times[-1] > now - 60}
        if address not in self.clients and len(self.clients) >= 4096:
            raise HTTPException(503, "Server is busy. Try again shortly.", headers={"Retry-After": "60"})
        times = self.clients.setdefault(address, deque())
        while times and times[0] <= now - 60:
            times.popleft()
        if len(times) >= 10:
            raise HTTPException(429, "Request limit reached. Wait a minute and try again.", headers={"Retry-After": str(max(1, math.ceil(60 - (now - times[0]))))})
        times.append(now)


def create_app(database_path=None, transport=None):
    path = database_path or os.getenv("DATA_PATH", str(ROOT / "data" / "weather.json"))

    @asynccontextmanager
    async def lifespan(application):
        application.state.store = DocumentStore(path)
        async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=5), follow_redirects=False, transport=transport) as client:
            application.state.weather = WeatherClient(client)
            application.state.analysis_lock = asyncio.Lock()
            application.state.limiter = RateLimiter()
            try:
                yield
            finally:
                application.state.store.close()

    app = FastAPI(title="Climate Hazard Trend Analyzer", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        # FastAPI's documentation uses CDN assets and an inline Swagger bootstrap.
        if request.url.path in {app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://fastapi.tiangolo.com; "
                "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(OSError)
    async def disk_error(request, exc):
        logger.exception("Document cache storage failure", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "Data storage is unavailable. Check the server disk and try again."})

    @app.get("/api/health")
    async def health():
        app.state.store.get("analyses", "health-check")
        return {"status": "ok", "latest_complete_year": datetime.now(timezone.utc).year - 1}

    @app.post("/api/analyze")
    async def analysis(query: AnalysisRequest, request: Request):
        app.state.limiter.check(request.client.host if request.client else "unknown")
        latitude, longitude = round(query.latitude, 4), round(query.longitude, 4)
        key = f"{latitude:.4f}:{longitude:.4f}:{query.start_year}:{query.end_year}:v1"
        cached = app.state.store.get("analyses", key)
        if cached:
            return {**cached["data"], "cache": {"analysis_hit": True, "weather_hit": True,
                    "computed_at": datetime.fromtimestamp(cached["created_at"], timezone.utc).isoformat()}}
        try:
            await asyncio.wait_for(app.state.analysis_lock.acquire(), timeout=1)
        except TimeoutError:
            raise HTTPException(503, "Another weather analysis is running. Try again shortly.", headers={"Retry-After": "5"}) from None
        try:
            cached = app.state.store.get("analyses", key)
            if cached:
                return {**cached["data"], "cache": {"analysis_hit": True, "weather_hit": True,
                        "computed_at": datetime.fromtimestamp(cached["created_at"], timezone.utc).isoformat()}}
            start = date(min(query.start_year, 1991), 1, 1)
            end = date(max(query.end_year, 2020), 12, 31)
            weather_key = f"{latitude:.4f}:{longitude:.4f}:{start}:{end}:era5:v1"
            weather_document = app.state.store.get("weather", weather_key)
            weather_hit = weather_document is not None
            if weather_hit:
                weather = weather_document["data"]
            else:
                try:
                    weather = await asyncio.wait_for(app.state.weather.fetch(latitude, longitude, start, end), timeout=75)
                except TimeoutError:
                    raise HTTPException(504, "Weather request exceeded the overall time limit. Try again later.") from None
                app.state.store.put("weather", weather_key, weather, ttl=7 * 24 * 3600)
            try:
                result = analyze(weather["records"], query.start_year, query.end_year)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            result.update({"location": {"latitude": latitude, "longitude": longitude},
                           "period": {"start_year": query.start_year, "end_year": query.end_year},
                           "source": weather["source"], "hazard": "heatwave"})
            app.state.store.put("analyses", key, result, ttl=24 * 3600)
            persisted = app.state.store.get("analyses", key)
            return {**persisted["data"], "cache": {"analysis_hit": False, "weather_hit": weather_hit,
                    "computed_at": datetime.fromtimestamp(persisted["created_at"], timezone.utc).isoformat()}}
        finally:
            app.state.analysis_lock.release()

    frontend = Path(os.getenv("FRONTEND_DIST", str(ROOT.parent / "frontend" / "dist")))
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
