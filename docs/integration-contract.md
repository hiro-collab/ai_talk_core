# Integration Contract

`ai-talk-core` と統合側の接続契約です。ここには外部から呼ぶ入口、payload、保存物、互換名だけを書きます。

## 接続範囲

- このモジュールはローカルホスト上で動く音声入力フロントエンドです。
- 外部 adapter は gesture、keyboard、network signal などを `input_enabled` へ変換してから渡します。
- 外部 agent backend は保存済み handoff または runner CLI 経由で受け取ります。
- Web/API はローカル利用前提であり、インターネット公開しません。

## CLI Entrypoints

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
uv run python -m src.main --mic --duration 5 --language ja
uv run python -m src.main --mic-loop --duration 3 --language ja
uv run python -m src.main --doctor --doctor-format json
```

保存済み handoff を読む:

```bash
uv run python -m src.agent_handoff --source web --format prompt
```

保存済み handoff を外部コマンドへ渡す:

```bash
uv run python -m src.agent_runner --source web --template cat
```

`src.codex_handoff` と `src.codex_runner` は互換入口です。統合側の新規接続は `agent_*` 側を使います。

## Compatibility Policy

主導線:

- `src.agent_handoff`
- `src.agent_runner`
- `/api/agent-handoff-latest`
- `instruction_only`
- `save_handoff`
- `--handoff-output`

互換入口:

- `src.codex_handoff`
- `src.codex_runner`
- `/api/codex-handoff-latest`
- `command`
- `command_only`
- `save_command`
- `--command-output`
- `.cache/codex/`

互換入口は、統合側の呼び出し元と smoke coverage が主導線へ移ったことを確認し、この文書と該当テストを同じ変更で更新するまで残します。削除判断は archive の作業ログから復活させず、接続契約の変更として扱います。

互換入口を残す間は、主導線と同じ transcript / instruction / handoff を返します。挙動を分岐させません。

## Web Server

```bash
uv run python -m src.web.app
```

Windows helper:

```powershell
.\start_web.ps1 -Token local-dev-token
```

外部プロセスから保護 API を呼ぶ場合:

- 起動環境変数: `AI_TALK_CORE_WEB_TOKEN`
- primary header: `X-AI-Core-Token`
- compatibility header: `X-Sword-Agent-Token`
- bearer token: `Authorization: Bearer <token>`

## Transcription API

`POST /api/transcribe-upload`

- form field: `audio_file`
- optional fields: `model`, `language`, `instruction_only`, `command_only`, `save_handoff`, `save_command`

`POST /api/transcribe-browser-recording`

- form field: `audio_blob`
- optional fields are the same as file upload.

Response fields include:

- `transcript`
- `command`
- `prompt_text`
- `command_path`
- `command_text_path`
- `error`

`command` remains a compatibility field for instruction draft text.

## Input Gate API

`GET /api/input-gate` returns gate state.

`POST /api/input-gate` accepts JSON:

```json
{
  "input_enabled": true,
  "reason": "external_signal",
  "source": "integration_adapter"
}
```

The core module does not know gesture names or adapter-specific semantics. The integration side owns that translation.

## Status And Events

`GET /api/health` and `GET /api/status` return the same shape and include server, STT, input gate, event log, and handoff status.

Event endpoints:

- `POST /api/events/ingest`: client timing events
- `GET /api/events`: Server-Sent Events stream or `?once=true` snapshot
- `POST /api/recording-chunk`: browser recording chunk metadata and cache file

These endpoints require the local API token.

## Handoff Artifacts

Saved handoff bundles contain transcript, instruction draft, source, id, timestamp, and metadata.

Default Web source paths:

- `.cache/codex/web_latest.json`
- `.cache/codex/web_latest.txt`

The `codex` directory name and `web_latest` file name are compatibility artifacts. They do not define the active documentation route.

Handoff read endpoints:

- `GET /api/agent-handoff-latest?source=web`
- `GET /api/codex-handoff-latest?source=web`

The `codex` endpoint is kept for compatibility.

## Shutdown

`POST /api/shutdown` requests Web server shutdown.

```json
{
  "reason": "integration_finished",
  "force": false
}
```

The request stops additional work and lets active transcription finish unless `force` is true. It does not safely interrupt Whisper/Torch execution already in progress.
