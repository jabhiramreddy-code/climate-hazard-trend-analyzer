# Verification record

## Executed checks

- Read both pages of the supplied case study using PDF content-stream extraction.
- Read back the created project files.
- Parsed App.jsx, TrendChart.jsx, main.jsx, export.js, export.test.js, and vite.config.js with the Babel JSX parser from the local npm cache. All six parsed successfully.
- Executed nine direct assertions against the actual CSV module in the Node runtime. Quoting, embedded newlines, formula protection, missing values, annual data, methodology metadata, CRLF rows, and numeric negative coordinates/temperatures passed.

- Parsed the Docker CMD as JSON and checked its shell arguments. This is not a Docker build/run test.
- Completed an independent read-only review; see [review decisions](REVIEW.md).

## Environment blockers

The shell tool cannot create a process: helper_unknown_error: setup refresh had errors. This occurred for workspace discovery, an explicit PowerShell invocation, and the Python test command. A Python process requested from the Node runtime also returned EACCES. Direct package/API network requests from Node returned EACCES.

An attempt to use Node's in-process test runner timed out and reset its kernel. That attempt is not counted as a passing test run. The first seven direct CSV assertions and five Babel parse checks completed before the reset. Final checks after reviewer corrections executed nine CSV assertions, parsed six files, and parsed Docker CMD JSON successfully.

## Required before submission

Run these from the repository root after restoring normal process/network access:

1. python -m venv .venv
2. .\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
3. .\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -q
4. In frontend: npm install, npm test, and npm run build.
5. Start Python and Vite using README.md, then analyze New Delhi for 1990–2020 using real Open-Meteo data. Repeat it to check the stored-analysis indicator.
6. Check custom coordinates, invalid dates, chart metric switches, CSV download, empty-event results, event and annual tables, keyboard access, and mobile layout. Configure and verify trusted proxy handling and durable storage for the chosen deployment.
7. Build/run Docker and verify /api/health and the frontend from the same origin.
8. Push source to GitHub (excluding the PDF), deploy, test the public URL, then submit the two links.

Python tests, the production build, live provider integration, visual rendering, Docker execution, GitHub publication, and deployment have not been verified in this session. Source implementation does not imply those checks passed.
