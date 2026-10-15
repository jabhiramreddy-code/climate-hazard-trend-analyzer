# Climate Hazard Trend Analyzer

A React and Python web application for exploring historical heatwave frequency, duration, and intensity at a selected city or coordinate.

**Implementation status:** local checks are complete: 39 backend tests passed (user-reported rerun after the test dependency adjustment), three frontend tests passed, the frontend production build succeeded, and all ten manual browser checks passed. Local cache reuse after a backend restart is confirmed for New Delhi and Bengaluru. The Docker container starts successfully and serves the API and built React assets; supplied logs show successful analysis requests. The user confirmed cached results survive container replacement with the same named volume. Public repository publication, hosted deployment and submission remain pending. See [TODO.md](TODO.md) and the [verification record](docs/VERIFICATION.md) for evidence and remaining hosting checks.

## Features

- Ten city presets and custom latitude/longitude.
- Heatwave selected by default; complete calendar years from 1940 to the latest completed year.
- Interactive Chart.js views of annual event count, mean event duration, and mean temperature exceedance, with three-year rolling averages.
- Descriptive linear regression slopes per decade and R², subject to coverage and sample-size checks.
- Annual data and detected-event tables, coverage warnings, and methodology notes.
- Formula-safe CSV export including the location, threshold, baseline, source, and model.
- Python ingestion of real Open-Meteo ERA5 data, with persistent NoSQL caches for daily records and computed results.
- Input validation, request limits, bounded weather responses, timeouts, atomic database replacement, and controlled error responses.

The application fetches real weather when an analysis is requested. It does not silently substitute demonstration or synthetic weather.

## Local setup on Windows

Prerequisites: Python 3.11 or newer, Node.js 22.12 or newer, and internet access to install packages and reach Open-Meteo.

From the repository root, in PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-proxy-headers
~~~

Open a second terminal in the repository root:

~~~powershell
cd frontend
npm install
npm run dev
~~~

Open http://localhost:5173. Select a city and year range, then click **Analyze heatwaves**. The first request fetches the baseline and selected history; later identical requests use stored results. Vite proxies /api to Python on port 8000.

On macOS/Linux, use .venv/bin/python in place of .\.venv\Scripts\python.exe. The remaining commands are the same.

### Production frontend served by Python

~~~powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
~~~

Open http://localhost:8000. FastAPI mounts frontend/dist when it exists at startup. Restart Python after creating the build.

### Tests

From the repository root:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -q
cd frontend
npm test
npm run build
~~~

The backend suite exercises actual climate calculations, TinyDB storage and FastAPI routes. Only the external HTTP transport is replaced with deterministic daily-weather fixtures. It covers strict percentile comparison, minimum duration, gaps, unit conversion, malformed/outlier values, year boundaries, baseline/annual coverage, regression, persisted cache reuse, expiry, bad inputs, provider errors/timeouts, and rate limiting.

The frontend tests cover CSV quoting, spreadsheet-formula protection, output values, metadata, and line endings. Build and browser checks are separate from these unit tests.

## Architecture

~~~text
React form → POST /api/analyze → FastAPI validates coordinates/years
                              → TinyDB analysis cache
                              → TinyDB weather cache, if analysis is absent
                              → fixed-host Open-Meteo ERA5 fetch, if weather is absent
                              → normalize daily records → detect events → annual summaries
                              → persist analysis → return stored JSON
React ← JSON → Chart.js / annual table / event table / CSV
~~~

| Path | Responsibility |
| --- | --- |
| backend/app/analysis.py | Schema cleaning, percentile, heatwave detection, coverage, annual aggregation, rolling averages, OLS |
| backend/app/models.py | HTTP input validation |
| backend/app/weather.py | Fixed-host public API access and upstream failure handling |
| backend/app/store.py | TinyDB document persistence, atomic writes, TTL and bounded cache eviction |
| backend/app/main.py | FastAPI lifecycle, routes, request limiting, analysis serialization and static frontend |
| backend/tests/ | Climate, database and API acceptance tests |
| frontend/src/App.jsx | Selection controls, request states and results |
| frontend/src/TrendChart.jsx | Chart.js lifecycle and interactive charts |
| frontend/src/export.js | CSV encoding and browser download |
| Dockerfile / render.yaml | Same-origin container deployment |

[TinyDB](https://tinydb.readthedocs.io/en/latest/intro.html) is a document-oriented NoSQL database implemented in Python. It avoids a database service/account for this small assessment. The JSON file is owned by one process; an in-process lock protects access, and writes flush to a temporary file before atomic replacement. It is not a substitute for MongoDB at larger scale.

No previous application existed in this directory. The change introduces the modules, their frontend/API callers, tests, build configuration, deployment files, and documentation; it changes no existing user data.

## API

### GET /api/health

Returns status and latest_complete_year without making an external weather request. FastAPI's interactive API documentation is at /docs.

### POST /api/analyze

~~~json
{
  "latitude": 28.6139,
  "longitude": 77.209,
  "start_year": 1990,
  "end_year": 2020,
  "hazard": "heatwave"
}
~~~

hazard can be omitted and defaults to heatwave. Unknown properties and unsupported hazards are rejected. Coordinates must be finite and within geographic bounds; year values must be integers in order and refer to completed years.

~~~powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/analyze -ContentType 'application/json' -Body '{"latitude":28.6139,"longitude":77.209,"start_year":1990,"end_year":2020,"hazard":"heatwave"}'
~~~

The JSON response includes location, period, hazard, source, methodology, quality, summary, annual, events, trends, and cache. Chart-ready annual rows include events, heatwave_days, mean_duration, mean_exceedance, peak_temperature, coverage, eligible, and rolling values. Unavailable rolling/regression values are null, rather than fabricated zero trends.

| HTTP code | Meaning |
| --- | --- |
| 200 | Analysis read from the document store |
| 422 | Invalid input or insufficient reference-baseline coverage |
| 429 | Local request limit exceeded; Retry-After supplied |
| 502 | Provider unreachable, unsuccessful, oversized or malformed |
| 503 | Provider rate limit, busy analyzer, or unavailable storage |
| 504 | Provider read/connect or overall request timeout |

## Data source and attribution

The backend uses the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), requesting daily temperature_2m_max, models=era5, temperature_unit=celsius, and timezone=auto. ERA5 is available from 1940 and is explicitly chosen to avoid mixing model generations across decades. These are gridded reanalysis estimates, not direct city station measurements.

The backend fetches one continuous interval spanning both the requested years and the fixed 1991–2020 baseline. This avoids separate baseline and analysis calls for the same request. Dates use the provider's local daily timezone; provider grid coordinates are returned and displayed alongside the requested point.

Weather data attribution: Open-Meteo and Copernicus Climate Change Service / ECMWF ERA5. The data is supplied under [CC BY 4.0](https://open-meteo.com/en/licence). Review [Open-Meteo terms](https://open-meteo.com/en/terms) for API usage; the free endpoint is intended for non-commercial use and has usage limits.

## Hazard logic and data quality

1. Validate upstream array lengths, supported temperature units, ISO dates, uniqueness, and requested bounds.
2. Normalize Celsius, Fahrenheit, or Kelvin to Celsius. Null, nonnumeric, boolean, or nonfinite temperatures are missing. Values outside −90 to 65 °C are flagged as outliers and excluded. Real hot extremes within these conservative bounds are retained.
3. Fill absent calendar dates with missing observations. Never interpolate a missing day or replace it with zero.
4. Require at least 90% valid days overall and in **every year** of the 1991–2020 baseline. If that fails, return a visible error.
5. Calculate the pooled regional baseline's 95th percentile using linear rank interpolation. For sorted values, rank = (n − 1) × 0.95; interpolate between adjacent ranks.
6. A heatwave is at least three consecutive calendar days with daily maximum temperature **strictly above** the unrounded threshold. Equality is not exceedance; missing/invalid/outlier days end the run.
7. Count an event in the year it starts. Allocate heatwave days and daily temperature exceedance to their actual calendar years. Report a December–January event once.
8. Include every selected year, including zero-event years. Show coverage and mark years below 90% as ineligible for trend calculations.

Intensity means the average temperature exceedance above the threshold on heatwave days. It is not humidity-adjusted heat index or an official severity classification. Duration is the mean full duration of events starting that year. Annual duration/intensity are zero in years without the corresponding observed events/days.

### Trends and honest interpretation

Three-year trailing averages require all three consecutive calendar years to meet the coverage threshold. A missing/ineligible year breaks a rolling window.

OLS uses actual calendar-year values and at least five eligible years; skipped years are not compressed. Slopes are reported per decade for event count, annual mean duration, and annual mean exceedance. R² describes fit; it is null when the series is constant.

These estimates are descriptive. They are not significance tests, climate attribution, local warning thresholds, forecasts, or health-risk estimates. Missing days can hide events or split one event into multiple detections, so frequency can be biased in either direction. Even an eligible year can have gaps.

## Caching, security and performance

- Daily weather documents: seven-day TTL, at most eight documents.
- Analysis documents: 24-hour TTL, at most 32 documents.
- Keys include coordinates rounded to four decimal places, interval, model, and methodology version. Identical requests reuse persisted results, including after process restart when the database file is retained.
- Expired/oldest documents are removed during writes. No provider error is stored as successful data.
- No user-supplied URLs. Outbound requests go to a fixed HTTPS host, do not follow redirects, cap decoded responses at 16 MiB, use five-second connection and 45-second operation timeouts, and have a 75-second overall limit.
- Rate limit: ten analysis requests per network peer per rolling minute. Idle limiter entries expire and the client-key count is bounded.
- One uncached analysis runs at a time. A competing request waits up to one second, then receives a retryable busy response. Analysis/cache paths share the same lock, preventing duplicate fills in one worker.
- Same-origin frontend/API, React text escaping, restrictive response headers, bounded full-year range, and spreadsheet-formula-safe CSV cells.
- The container enables Uvicorn proxy handling with FORWARDED_ALLOW_IPS defaulting to 127.0.0.1. Behind a hosting proxy, peers can share the request limit until that proxy's verified IP addresses/CIDRs are configured. Configure only known trusted proxies; do not trust arbitrary X-Forwarded-For values. See [Uvicorn proxy settings](https://www.uvicorn.org/settings/). This deployment check remains outstanding.
- Run **one worker and one replica** for the TinyDB file. The bounded document cache still rewrites a JSON file and performs synchronous local I/O, so this implementation is intended for small assessment/demo traffic.

## Docker and deployment

~~~powershell
docker build -t climate-analyzer .
docker run --rm -p 8000:8000 --mount type=volume,source=climate-data,target=/app/data climate-analyzer
~~~

The container builds React, installs Python requirements, serves both on one origin, runs as a non-root user, and uses one Uvicorn worker. The named Docker volume retains the database across container replacement.

For Render, connect the source repository and create a Blueprint using render.yaml, or create a Docker Web Service manually. The included configuration uses the free plan, /api/health, and DATA_PATH=/tmp/climate/weather.json.

[Render free services](https://render.com/docs/free) have an ephemeral filesystem and can spin down: caches are lost on restart, redeploy, or spin-down, and a later request re-downloads weather. For durable hosted NoSQL storage, use a paid persistent disk with DATA_PATH on its mount, or replace TinyDB with a managed MongoDB database before deploying replicas. Local/Docker volume persistence is supported independently of the hosting limitation.

Environment variables:

| Variable | Default | Use |
| --- | --- | --- |
| DATA_PATH | backend/data/weather.json | Writable NoSQL cache file |
| FRONTEND_DIST | frontend/dist | Built frontend directory |
| PORT | 8000 in Docker | Hosting platform's listening port |
| FORWARDED_ALLOW_IPS | 127.0.0.1 | Verified trusted proxy addresses/CIDRs; never an unverified wildcard |

No application credentials are required for local use. frontend/package-lock.json is present and Docker uses npm ci; commit the lockfile with the source. Python dependencies currently use bounded version ranges; pinning the verified Python dependency set would further improve deployment reproducibility.

### Submission steps remaining

1. Backend tests, the frontend build and the manual real-data browser flow have user-reported passes. Frontend npm test output confirms three passes. The test dependency adjustment and backend rerun are complete; local cache reuse after a backend restart is confirmed.
2. Create a public GitHub repository and push the source. **Exclude the confidential assessment PDF**, already covered by .gitignore and .dockerignore.
3. Deploy the container, test the live URL, and submit the repository/app URLs through the separately supplied submission form.
4. Disclose AI use in the submission form. A demo recording is optional.

Repository and deployed URLs do not yet exist in this delivery. No submission has been sent.

## Assumptions and improvements with more time

The selected region is one point/grid cell. City presets are conveniences, not area aggregates. The pooled annual p95 favors the hottest season; a calendar-day percentile baseline would capture anomalous heat in other seasons. Boundary-touching events can be truncated, and runs shorter than three observed days at a boundary may be missed. The current partial year is excluded.

With more time: verify the production and scientific behavior against known records; use a seasonal threshold and baseline uncertainty estimates; add event-boundary context; move documents to MongoDB with indexes and shared rate limits; cache reusable location/year chunks; pin tested dependencies; add browser-level tests and a region map. Additional hazards and PDF export are intentionally outside the core scope.

## AI tools used

OpenAI Codex was used to interpret the brief, plan the work, create documentation, draft the React/Python source and tests, inspect official provider/hosting documentation, and perform available source/CSV checks. A separate Codex reviewer was used for a read-only code review. The author should review and understand all code and be prepared to explain or modify it during an interview. Unexecuted checks are disclosed above.
