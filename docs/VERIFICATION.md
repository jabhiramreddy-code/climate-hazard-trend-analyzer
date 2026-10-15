# Verification record

Last updated: 2026-10-15. Results below distinguish developer-run checks from checks performed through Codex tools.

## Developer-run checks

- **Backend:** latest reported rerun passed all 39 tests after installing the updated development requirements. The preceding pasted output showed 39 passed, 1 warning in 2.06 seconds. The warning concerned Starlette TestClient's deprecated HTTPX fallback; `httpx2>=2,<3` was added to development requirements. Warning-free output was not separately supplied.
- **Frontend:** pasted `npm test` output showed 3 passed and 0 failed in 158.227 ms. The production build was confirmed successful.
- **Manual browser checks:** New Delhi 1990–2020; frequency, duration and intensity charts and tooltips; annual and event tables; CSV values compared with displayed data; another city and custom coordinates; invalid year validation; loading/error states; phone-sized layout; Tab/Enter controls; and backend logs were confirmed working.
- **Local persistence:** after stopping and restarting the backend, previously analyzed New Delhi and Bengaluru returned stored results.
- **Docker:** supplied runtime logs showed successful startup and three analysis requests returning HTTP 200. After stopping and rerunning the container with the same `climate-data` named volume, the developer confirmed Stored analysis.

## Checks performed through Codex tools

- Read both pages of the supplied assessment and reviewed the project files.
- Parsed all six frontend JavaScript/JSX files with Babel. Executed nine direct assertions against the CSV module, including escaping, formula protection, metadata, CRLF rows and preservation of negative numeric values. Parsed Docker CMD as JSON.
- Completed an independent read-only source review and applied corrections; see [review decisions](REVIEW.md).
- Confirmed local New Delhi and Bengaluru cache hits through HTTP. Returned summaries and computation timestamps matched persisted TinyDB documents.
- Confirmed the local Docker service returned HTTP 200 for health, frontend HTML and the built JavaScript asset. A clean image rebuild was not independently run.

### API documentation fix

The local /docs route originally returned HTML whose Content Security Policy blocked Swagger's CDN assets and inline initialization. Documentation-specific permissions were added while application/API responses retained their strict policy. Direct HTTP assertions passed for /docs, /docs/oauth2-redirect, /redoc, /api/health, /openapi.json, / and an unknown documentation path. Seven parameterized regression cases were added to the backend suite subsequently run by the developer. Documentation assets still require external CDN access.

The reported 404 for /.well-known/appspecific/com.chrome.devtools.json is optional [Chrome DevTools workspace discovery](https://developer.chrome.com/docs/devtools/automatic-workspaces), unrelated to the analyzer.

### Public deployment and repository

Connected Chrome checks at [the Render deployment](https://climate-hazard-trend-analyzer-2ljf.onrender.com/) confirmed:

- The application loaded and /api/health returned status ok and latest_complete_year 2025.
- New Delhi, 1990–2020, returned Stored analysis: 71 events, 428 heatwave days, longest event 21 days, threshold 41.5 °C and 100% coverage.
- Mumbai, 1990–2020, completed: 54 events, 222 heatwave days, longest event 10 days, threshold 33.7 °C and 100% coverage. Repeating the request returned Stored analysis.
- Duration, Intensity and Frequency controls changed the chart metric labels.

[GitHub](https://github.com/jabhiramreddy-code/climate-hazard-trend-analyzer) displayed the Public badge. The inspected main commit was `1757f3efcc19dba2da35e6655e6f423bcb9b3a80`; its Go to file query for .pdf returned no matches. This checked current filenames, not the complete Git history or a separate unsigned browser session.

## Limits and remaining work

- Codex's shell runner could not start processes, and direct Node network requests were blocked. Standard pytest/npm/build commands were run by the developer; Codex used file inspection, direct assertions, reachable local HTTP and connected Chrome for its checks.
- A standalone automated browser suite, a public CSV download comparison, a provider network trace, cold-start recovery, durable hosted storage and separate-client proxy/rate-limit behavior were not tested. The complete local manual checklist was not repeated on the public deployment.
- Render's free filesystem is ephemeral. Hosted caches can be lost on restart, redeploy or spin-down; this does not affect the confirmed local and Docker-volume persistence results.
- Commit and push the final documentation, then submit the repository and deployment URLs with the AI-use disclosure through the external assessment form. The form has not been submitted.
