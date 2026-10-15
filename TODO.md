# Assessment implementation plan

**Current status:** implementation, local tests/build/browser checks, local persistence, Docker runtime/volume persistence, public repository publication and Render deployment are complete. Live browser checks confirmed health, New Delhi and Mumbai analyses, repeated-request cache reuse and chart metric switches. Publish the final documentation changes and submit the external assessment form. Production hardening options remain listed separately below.

**Verification:** see [the current verification record](docs/VERIFICATION.md) for local test results, browser and persistence checks, and their limits. See [review decisions](docs/REVIEW.md) for source-review corrections.

**Goal:** Deliver the heatwave analyzer described in README.md, including runnable source, meaningful tests, setup and deployment documentation.

**Architecture:** React consumes a same-origin FastAPI JSON API. Python caches cleaned ERA5 daily records and computed results in TinyDB. A single Docker service builds and serves both parts.

## 1. Climate analysis

Files: backend/app/analysis.py; backend/tests/test_analysis.py.
Interface: normalize_weather(payload, start, end) returns daily Celsius records and quality counts. analyze(records, start_year, end_year) returns methodology, annual metrics, events, summary and trends.

- [x] Write tests for percentile interpolation, strict threshold, minimum duration, missing calendar dates, invalid observations, Fahrenheit conversion, cross-year allocation, zero-event years, low coverage and hand-calculated regression.
- [x] Implement normalization, fixed-baseline threshold, run detection and annual aggregation.
- [x] Implement three-year rolling averages and per-decade OLS slopes with R².
- [x] Run the climate tests as part of the backend suite (latest reported suite result: 39 passed).

## 2. Persistence and API

Files: backend/app/models.py, store.py, weather.py, main.py; backend/tests/test_api.py; requirements files.
Interface: POST /api/analyze accepts latitude, longitude, start_year, end_year, hazard. GET /api/health provides readiness. JSON contains location, period, methodology, quality, annual, events, summary, trends and cache metadata.

- [x] Write tests for invalid coordinates/years, cache reuse and expiry, database reopening, malformed upstream data, timeout, upstream rate limit, local rate limit and health.
- [x] Validate finite coordinates and ordered completed years at the HTTP boundary.
- [x] Implement fixed-host HTTPX retrieval with bounded response size, timeout, redirects disabled and sanitized errors.
- [x] Persist daily records and analyses in TinyDB, with TTLs, bounded cache size and a serialized access lock.
- [x] Apply per-network-peer request limits and a global cap on concurrent upstream analysis.
- [x] Run all backend tests (latest reported rerun: 39 passed on 2026-10-15; warning details are in the verification record).
- [x] Review the pytest warning: Starlette 1.8.0 TestClient prefers httpx2; add httpx2>=2,<3 to development requirements.
- [x] Install updated development requirements and rerun pytest (user-reported: 39 passed after the httpx2 adjustment; warning-free output was not separately supplied).

## 3. React dashboard

Files: frontend/package.json, index.html, vite.config.js, src/App.jsx, src/TrendChart.jsx, src/export.js, src/styles.css, src/main.jsx; frontend/tests/export.test.js.
Interface: same-origin /api/analyze; Vite proxies /api during local development.

- [x] Build city/custom-coordinate selection, default heatwave control, year range, validation and loading/error states.
- [x] Display frequency, mean duration and mean temperature exceedance in interactive charts with rolling averages.
- [x] Show threshold, data coverage, regression interpretation, annual table, event table and transparent methodology.
- [x] Add CSV export with formula-safe cells and test CSV quoting/line endings.
- [x] Execute nine CSV assertions in the available Node runtime and parse all six frontend JavaScript/JSX files.
- [x] Run the standard npm test command (pasted output: 3 passed, 0 failed; total duration 158.227 ms on 2026-10-15).
- [x] Run the frontend production build (user-confirmed successful on 2026-10-15).
- [x] Verify browser flow, keyboard controls and narrow-screen layout (user-confirmed 2026-10-15; all ten manual browser checks passed; see docs/VERIFICATION.md).

## 4. Packaging and submission

Files: Dockerfile, .dockerignore, .gitignore, render.yaml, README.md, docs/VERIFICATION.md.

- [x] Add single-service container, persistent Docker volume instructions, and an explicitly ephemeral Render free-tier configuration.
- [x] Verify local Docker startup, successful analysis requests, /api/health, built frontend HTML and JavaScript serving (user logs and live HTTP checks).
- [x] Verify the named Docker volume retains cached results across container replacement (user-confirmed Stored analysis after stopping and rerunning the container on 2026-10-15).
- [x] Document free-tier cache loss and the persistent-disk/MongoDB options; durable hosted storage is an optional upgrade.
- [x] Document the trusted-proxy limit: default trust remains 127.0.0.1; separate-client buckets are not verified.
- [x] Complete README with setup, API, architecture, source attribution, methodology, assumptions, improvements, and AI disclosure.
- [x] Record actual checks and unresolved environment limitations.
- [x] Complete real-data browser analysis and manual UI checks (user-confirmed 2026-10-15).
- [x] Confirm persisted cache reuse after a backend restart (user-confirmed; live API returns analysis_hit=true and database-matching summaries for New Delhi and Bengaluru, 1990–2020).
- [x] Record user-supplied repository URL: https://github.com/jabhiramreddy-code/climate-hazard-trend-analyzer (local origin matches).
- [x] Verify the GitHub Public badge and current-branch PDF exclusion (Chrome: Go to file search for .pdf returned No matches found).
- [x] Deploy and verify https://climate-hazard-trend-analyzer-2ljf.onrender.com/ (health, analysis, repeated-request cache and chart controls checked in Chrome).
- [ ] Commit and push the final documentation updates.
- [ ] Submit the repository and deployment URLs using the external submission form.
- [ ] Include the AI-use disclosure in the submission form and submit before the deadline from the original assessment message. A demo recording is optional.

## Review focus

1. A missing day or invalid value must split an event rather than create a false consecutive run.
2. A heatwave crossing December/January must count once and allocate days to the correct years.
3. Baseline or annual coverage problems must be visible and must not yield confident trend claims.
4. Repeated requests must read persisted results; upstream or disk failures must not become fake successful data.
5. CSV export must not execute spreadsheet formulas from user-controllable text.

## Optional work

CSV export and linear regression are included. Additional hazards, a map, PDF export and a demo recording are optional extensions.

### Optional production hardening

- [ ] Use durable hosted NoSQL storage if the cache must survive hosting restarts/redeploys.
- [ ] Configure verified hosting proxy addresses/CIDRs and verify separate-client rate-limit buckets.
- [ ] Check cold-start recovery and repeat key browser checks from a separate device/network.

These are disclosed hosting limitations and further hardening checks, not missing mandatory features in the assessment brief.
