# Changelog

## 2026-04-28 - Local Web API security hardening

Reviewed the updated `main` after the Web integration status controls were added.

### Security risks addressed

- Status/control APIs exposed local runtime state without the local UI token:
  `/api/doctor`, `/api/health`, `/api/status`, and `/api/input-gate`.
- Host header checks alone were not enough if the local server is accidentally
  exposed or proxied; the TCP peer address now also has to be loopback.
- Access-control failures could render the normal Web UI, which includes the
  per-process API token in `data-api-token`.

### Changes

- Added `request.remote_addr` loopback validation in `src/web/app.py`.
- Added token protection to doctor, health/status, and input-gate APIs.
- Added access-policy error responses that do not render token-bearing HTML.
- Added optional `AI_TALK_CORE_WEB_TOKEN` for local adapters/watchers that need
  a stable token across process starts.
- Updated `start_web.ps1` to accept `-Token`.
- Updated README API examples to show the required `X-AI-Core-Token` header.
- Added smoke tests for token requirements, loopback peer validation, and
  token-leak prevention on policy denials.

### Verification

- `python -m py_compile src\web\app.py smoke_test.py`
- `uv run python smoke_test.py`
  - 162 tests
  - OK

