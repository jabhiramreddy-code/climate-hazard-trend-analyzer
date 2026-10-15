# Code review and implementation decisions

A separate read-only Codex reviewer inspected the Python calculations, API/cache path, React response contracts, tests, and deployment configuration. It found no critical source defects. This is a source review, not evidence that the application executes successfully.

## Corrections

- CSV formula protection was applied to numeric negatives as well as strings. A direct assertion failed for Sydney's latitude before the fix. Protection now applies to strings only; numeric negatives remain numeric CSV cells. Regression assertions passed after the fix.
- Low-coverage frequency was described as a lower bound. A gap can hide an event or split one long event into two qualifying runs. UI and README now state that event frequency can be biased in either direction.
- Docker disabled all proxy handling, making it impossible to configure a trusted deployment proxy. The command now enables Uvicorn proxy handling with FORWARDED_ALLOW_IPS, defaulting to loopback; arbitrary public forwarded headers are not trusted.

## Rulings and remaining verification

- **Free hosting versus durable hosted storage:** Render's free tier has no persistent disk. The default configuration is explicitly an ephemeral demo; Docker named-volume persistence and local file persistence are supported. Durable hosted storage remains a submission/deployment choice: paid persistent disk or managed NoSQL. Cost if this limit is ignored: cold restarts lose cached records/results and require provider downloads.
- **Unknown proxy addresses:** No proxy CIDR or header sanitization was verified for an actual deployment. The default allowlist remains loopback rather than trusting all forwarded headers. Configuring and checking the hosting proxy is an unchecked TODO. Cost if ignored: users sharing a proxy can share a ten-request/minute bucket. Cost of blindly allowing all proxy addresses: client-IP spoofing could defeat the limiter.
- **Single worker:** TinyDB uses a single-process JSON file, so the supplied container runs one worker. Move to MongoDB/shared rate limits before replicas or additional workers.
- **Scientific boundaries:** A point/grid-cell analysis, pooled annual baseline and potentially truncated interval-boundary events are documented assumptions. They were considered in review and not treated as missing core features.

The Python suite, frontend production build, live Open-Meteo request, browser layout, Docker image and deployed proxy/storage behavior still need execution. The independent reviewer also encountered the command-runner setup error.
