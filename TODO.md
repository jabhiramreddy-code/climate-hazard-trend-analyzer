# Assessment implementation plan

**Current status:** source implementation and documentation provided; runtime verification, GitHub publication, deployment and submission remain pending.

**Available verification:** six frontend JavaScript/JSX files parsed; nine direct CSV assertions passed; Docker CMD JSON parsed. A separate read-only source review was completed and its corrections/remaining deployment limits are recorded in docs/REVIEW.md. Full command execution is blocked by the environment.

**Goal:** Deliver the heatwave analyzer described in README.md, including runnable source, meaningful tests, setup and deployment documentation.

**Architecture:** React consumes a same-origin FastAPI JSON API. Python caches cleaned ERA5 daily records and computed results in TinyDB. A single Docker service builds and serves both parts.

**Execution:** Implement directly in this workspace, which initially contains only the assessment PDF. No existing callers or data will be changed.

## 1. Climate analysis

Files: backend/app/analysis.py; backend/tests/test_analysis.py.
Interface: normalize_weather(payload, start, end) returns daily Celsius records and quality counts. analyze(records, start_year, end_year) returns methodology, annual metrics, events, summary and trends.

- [x] Write tests for percentile interpolation, strict threshold, minimum duration, missing calendar dates, invalid observations, Fahrenheit conversion, cross-year allocation, zero-event years, low coverage and hand-calculated regression.
Initial test-first execution was attempted before implementation, but the command runner failed to start. No red/green Python result is claimed.
- [x] Implement normalization, fixed-baseline threshold, run detection and annual aggregation.
- [x] Implement three-year rolling averages and per-decade OLS slopes with R².
- [ ] Run the climate tests and inspect failures.

## 2. Persistence and API

Files: backend/app/models.py, store.py, weather.py, main.py; backend/tests/test_api.py; requirements files.
Interface: POST /api/analyze accepts latitude, longitude, start_year, end_year, hazard. GET /api/health provides readiness. JSON contains location, period, methodology, quality, annual, events, summary, trends and cache metadata.

- [x] Write tests for invalid coordinates/years, cache reuse and expiry, database reopening, malformed upstream data, timeout, upstream rate limit, local rate limit and health.
Test-first API execution was unavailable because the command runner could not start processes. The tests are provided for execution once access is restored.
- [x] Validate finite coordinates and ordered completed years at the HTTP boundary.
- [x] Implement fixed-host HTTPX retrieval with bounded response size, timeout, redirects disabled and sanitized errors.
- [x] Persist daily records and analyses in TinyDB, with TTLs, bounded cache size and a serialized access lock.
- [x] Apply per-network-peer request limits and a global cap on concurrent upstream analysis.
- [ ] Run all backend tests.

## 3. React dashboard

Files: frontend/package.json, index.html, vite.config.js, src/App.jsx, src/TrendChart.jsx, src/export.js, src/styles.css, src/main.jsx; frontend/tests/export.test.js.
Interface: same-origin /api/analyze; Vite proxies /api during local development.

- [x] Build city/custom-coordinate selection, default heatwave control, year range, validation and loading/error states.
- [x] Display frequency, mean duration and mean temperature exceedance in interactive charts with rolling averages.
- [x] Show threshold, data coverage, regression interpretation, annual table, event table and transparent methodology.
- [x] Add CSV export with formula-safe cells and test CSV quoting/line endings.
- [x] Execute nine CSV assertions in the available Node runtime and parse all six frontend JavaScript/JSX files.
- [ ] Run the standard npm test command and production build.
- [ ] Verify browser flow, keyboard controls and narrow-screen layout.

## 4. Packaging and submission

Files: Dockerfile, .dockerignore, .gitignore, render.yaml, README.md, docs/VERIFICATION.md.

- [x] Add single-service container, persistent Docker volume instructions, and an explicitly ephemeral Render free-tier configuration.
- [ ] Configure durable hosted NoSQL storage if the deployed cache must survive restarts.
- [ ] Configure verified proxy addresses/CIDRs and check client rate-limit separation on the deployed service.
- [x] Complete README with setup, API, architecture, source attribution, methodology, assumptions, improvements, and AI disclosure.
- [x] Record actual checks and unresolved environment limitations.
- [ ] Run the full tests, build, live upstream smoke test and browser check.
- [ ] Create public GitHub repository containing source only and record its URL.
- [ ] Deploy the Python/React service and record a working URL.
- [ ] Submit the repository and deployment URLs using the external submission form.

## Review focus

1. A missing day or invalid value must split an event rather than create a false consecutive run.
2. A heatwave crossing December/January must count once and allocate days to the correct years.
3. Baseline or annual coverage problems must be visible and must not yield confident trend claims.
4. Repeated requests must read persisted results; upstream or disk failures must not become fake successful data.
5. CSV export must not execute spreadsheet formulas from user-controllable text.

## Optional work

CSV export and linear regression are included. Additional hazards, a map, PDF export, and a demo recording are deferred until the core application has been verified.
