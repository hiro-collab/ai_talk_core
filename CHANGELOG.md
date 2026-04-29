# Changelog

## 2026-04-29 - Latency event security hardening

Reviewed the updated `main` after latency event instrumentation was added.

### Security risks addressed

- Browser-origin event ingestion accepted arbitrary payload keys, which could
  persist transcript-like text or local debug data into `.cache/events.jsonl`.
- The event JSONL projection could grow without bound during repeated local
  recording sessions.
- Recording chunk uploads had only the whole-upload Flask limit and no
  per-chunk, per-turn, or sequence boundary.
- Recording chunk cache files could accumulate across repeated local recording
  sessions.
- Recording chunk events and health status could expose absolute local paths.
- Transcript event metadata retained a stable content hash, which is not needed
  for latency analysis.

### Changes

- Added bounded event payload sanitization for strings, lists, nesting, keys,
  non-finite numbers, and `Path` values.
- Added event log rotation at 5MB with a single `.1` archive.
- Added a client event payload allowlist for `/api/events/ingest`.
- Added recording chunk limits and removed absolute chunk paths from emitted
  events.
- Added recording chunk cache pruning by age, retained turn count, and total
  cache bytes.
- Changed health event log reporting to a project-relative cache path.
- Kept transcript-derived event metadata to length/presence only.

### Verification

- `uv run python -m py_compile src\core\events.py src\web\app.py src\web\transcription_service.py smoke_test.py`
- `uv run python -m unittest` for the added event/chunk hardening tests
  - 8 tests
  - OK
- `uv run python smoke_test.py`
  - 177 tests
  - OK

## 2026-04-28 - Local Web API security hardening

Reviewed the updated `main` after the Web integration status controls were added.

### Follow-up hardening

- Removed URL query token acceptance; local Web APIs now accept only the
  `X-AI-Core-Token` header.
- Added retrying smoke-test cleanup for transient Windows file locks around
  generated handoff artifacts.
- Strengthened README guidance that `AI_TALK_CORE_WEB_TOKEN` is required when
  external local adapters or watchers call protected APIs directly.

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
  - 163 tests
  - OK
