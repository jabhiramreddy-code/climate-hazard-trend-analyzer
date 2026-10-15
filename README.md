# Climate Hazard Trend Analyzer

A React and Python web application for exploring historical heatwave frequency, duration, and intensity at a selected city or coordinate.

**Live demo:** [Open the analyzer](https://climate-hazard-trend-analyzer-2ljf.onrender.com/)

**Source:** [GitHub repository](https://github.com/jabhiramreddy-code/climate-hazard-trend-analyzer)

## Features

- Ten city presets and custom latitude/longitude.
- Heatwave selected by default; complete calendar years from 1940 to the latest completed year.
- Interactive Chart.js views of annual event count, mean event duration, and mean temperature exceedance, with three-year rolling averages.
- Descriptive linear regression slopes per decade and R², subject to coverage and sample-size checks.
- Annual data and detected-event tables, coverage warnings, and methodology notes.
- Formula-safe CSV export including the location, threshold, baseline, source, and model.
- Python ingestion of real Open-Meteo ERA5 data, with persistent NoSQL caches for daily records and computed results.

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
npm ci
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

The backend tests cover heatwave calculations, data cleaning, coverage, regression, persisted caching, input validation, upstream failures and rate limiting. External weather requests use deterministic fixtures. Frontend tests cover CSV values, metadata, escaping and formula protection.

Latest local results: **39 backend tests passed**, **3 frontend tests passed**, and the production build succeeded. Browser and persistence checks are recorded in [docs/VERIFICATION.md](docs/VERIFICATION.md).

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

[TinyDB](https://tinydb.readthedocs.io/en/latest/intro.html) is a document-oriented NoSQL database. The weather and analyses collections store cleaned daily records and computed results in a local JSON file, avoiding a separate database service for this assessment.

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

The JSON response includes location, period, hazard, source, methodology, quality, summary, annual, events, trends, and cache. Chart-ready annual rows include events, heatwave_days, mean_duration, mean_exceedance, peak_temperature, coverage, eligible, and rolling values. Unavailable rolling/regression values are null.

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

- Weather cache: seven-day lifetime, at most eight documents. Analysis cache: 24-hour lifetime, at most 32 documents. Expired and oldest entries are removed during writes.
- Cache keys distinguish coordinates rounded to four decimal places and the requested interval; weather keys include the ERA5 model, and analysis keys include the methodology version. Identical requests reuse stored results while valid.
- Outbound requests use a fixed HTTPS host, reject redirects, cap responses at 16 MiB, and apply connection, operation and overall timeouts. Provider failures return controlled errors and are not cached as successful data.
- Coordinates, years and hazards are validated. Responses use security headers; React escapes text, and CSV export neutralizes spreadsheet formulas in string values.
- Analysis requests are limited to ten per network peer per minute. One uncached analysis runs at a time; competing requests receive a retryable busy response.
- The container trusts forwarded client addresses only from FORWARDED_ALLOW_IPS, defaulting to 127.0.0.1. Behind a hosting proxy, visitors may share a rate-limit bucket until verified proxy addresses are configured. See [Uvicorn proxy settings](https://www.uvicorn.org/settings/).

TinyDB uses atomic file replacement and is intended for small assessment/demo traffic. Run **one worker and one replica**; its synchronous JSON-file writes do not support scaling across processes.

## Docker and deployment

From the repository root, with Docker running:

~~~powershell
docker build -t climate-analyzer .
docker run --rm -p 8000:8000 --mount type=volume,source=climate-data,target=/app/data climate-analyzer
~~~

The container builds and serves React and FastAPI on one origin as a non-root user. The named Docker volume retains the database across container replacement.

For Render, connect the source repository and create a Blueprint using render.yaml, or create a Docker Web Service manually. The included configuration uses the free plan, /api/health, and DATA_PATH=/tmp/climate/weather.json.

[Render free services](https://render.com/docs/free) can spin down and use an ephemeral filesystem: caches are lost on restart, redeploy or spin-down, and later requests download weather again. Durable hosted caching requires persistent storage, such as a paid disk or a managed MongoDB database.

Environment variables:

| Variable | Default | Use |
| --- | --- | --- |
| DATA_PATH | backend/data/weather.json | Writable NoSQL cache file |
| FRONTEND_DIST | frontend/dist | Built frontend directory |
| PORT | 8000 in Docker | Hosting platform's listening port |
| FORWARDED_ALLOW_IPS | 127.0.0.1 | Verified trusted proxy addresses/CIDRs; never an unverified wildcard |

No weather API key is required for the configured public endpoint. Frontend dependencies are recorded in package-lock.json and installed with npm ci in Docker.

## Assumptions and limitations

- Each location represents one ERA5 grid cell. City presets and custom coordinates are points, not city-wide or state-wide averages or bounding boxes.
- The pooled annual 95th-percentile threshold emphasizes the hottest season. It is not a seasonally varying threshold or an official local warning definition.
- Events touching the selected interval can be truncated, and runs with fewer than three observed days at a boundary can be missed.
- The current partial calendar year is excluded.

## Improvements with more time

- Validate results against known records and add seasonal thresholds and uncertainty estimates.
- Fetch extra days around interval boundaries to detect complete events.
- Use MongoDB with indexes and shared request limits for multiple workers; cache reusable location/year chunks.
- Pin the verified Python dependencies and add an automated browser test suite.
- Add a region map, area aggregation or additional hazards after the core workflow.

## AI tools used and how

- **OpenAI Codex:** assisted with requirements interpretation, implementation, tests, documentation, deployment configuration and debugging.
- **Review agent:** one separate Codex agent performed an independent, read-only source review; the main assistant applied the resulting corrections.
- **Superpowers and Ponytail skills:** guided planning, debugging, review, verification and keeping the implementation small.
- **Browser automation / Playwright:** Computer Use tools with connected Chrome and Playwright-style locators checked deployed analyses, caching, chart controls, health and repository visibility. No standalone Playwright test suite was added.
- **Supporting tools:** a Node.js REPL handled file operations, PDF text extraction, syntax checks and CSV assertions. Web browsing checked official framework, dependency, weather-provider and hosting documentation.
