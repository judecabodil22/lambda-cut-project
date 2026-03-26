# Lambda Cut Changelog

All notable changes to this project documented here.

## 2.2 — 2026-03-26

### Listener & Process Management

| Change | Details |
|--------|---------|
| Stop mechanism added | Listener can now be stopped via `/stop_listener` Telegram command or `lambda_cut stop` CLI command |
| PID file | Listener writes PID to `/tmp/lambda_cut_listener.pid` for CLI stop command |
| Listener path fix | Fixed listener running from wrong directory (`lambda_cut_v2` → correct workspace) |
| Auto-stop existing listener | Starting a new listener automatically stops any existing one and notifies via Telegram |
| Auto-update systemd | Listener automatically updates systemd service to point to its installation directory |
| Listener status in /status | `/status` now shows listener running status, PID, and working directory |
| Logs include timestamp | `/logs` output now includes date and time for each entry |
| `/stop_pipeline` command | Stop the running pipeline mid-execution |
| `/delete_partial` command | Delete incomplete/partial files |
| `/cleanup` command | Delete all generated files from all output directories |
| `/clear_logs` command | Clear pipeline logs |
| `/set_index N` command | Set playlist index to download (e.g. 3rd video) |
| `-index N` CLI flag | Set playlist index via command line |
| Highest quality download | yt-dlp now downloads best available quality (4K/8K) |
| High quality clips | Phase 4 fixed: VAAPI uses `-rc_mode CQP -global_quality 10 -compression_level 1` instead of broken `-qp` parameter. CPU uses CRF 18 instead of 20 |
| Kdenlive automation | New `kdenlive_automation.py` script generates Kdenlive project files from template with updated paths, markers, and synced ASS subtitles. Output in `/output` directory |

### Bug Fixes

| Fix | Details |
|-----|---------|
| Telegram 400 error | Fixed by restarting listener from correct path |
| yt-dlp subprocess environment | Added `env=os.environ.copy()` to subprocess calls so Chrome cookies work properly |
| Phase 4 VAAPI quality | `-qp` parameter wasn't applied by ffmpeg (defaulted to QP 20). Now uses proper `-rc_mode CQP -global_quality 10` which actually applies the quality setting |
| Phase 5 TTS SRT | Changed stable-ts command to use `--output_format srt --word_timestamps false` for better transcription results |

---

## 2.1 — 2026-03-25

### Configuration & Setup

| Change | Details |
|--------|---------|
| Telegram made optional | Onboard asks "Use Telegram notifications? [y/N]". If no, `.env` omits Telegram keys. `/listen` exits with message if unconfigured. |
| Config guard for `run` | `lambda_cut run` refuses if `GEMINI_API_KEY` or `PLAYLIST_URL` is missing/empty. Telegram not required. |
| Workspace detection updated | `_find_workspace()` resolves from script's own directory. Removed hardcoded `~/lambda_cut` fallback. |
| Voice selection → numbered list | 30 Gemini TTS voices shown as numbered list. Current/default highlighted. User picks by number. |
| Gemini key prompt clarified | Now reads "Primary Gemini API Key (used for TTS; more keys added below)" |
| Telegram setup instructions | Step-by-step instructions for @BotFather token and @userinfobot chat ID printed before prompts |

### Pipeline & Listener

| Change | Details |
|--------|---------|
| Threaded pipeline | `run_pipeline()` runs in `threading.Thread(daemon=True)`. Listener stays responsive during pipeline execution. |
| `PIPELINE_RUNNING` flag | Global bool set `True` on start, `False` in `finally` block. Used by `/status` and `/config`. |
| `/status` simplified | Removed `pgrep` check. Uses `PIPELINE_RUNNING` + `/tmp/pipeline_status`. |
| `/config` simplified | Removed dead `psutil` import and `pgrep`. Uses `PIPELINE_RUNNING` flag. |
| `/logs` beautified | Filters timestamped `log()` lines only. Strips timestamps. Emoji: ✅❌⏳⏭️•. Bold `*Phase*` labels (Markdown). Path shortening. Noise filters for yt-dlp progress. |

### Bug Fixes

| Fix | Location | Details |
|-----|----------|---------|
| Whisper API | `lambda_cut.py:175,176,483` | `to_srt()` → `to_srt_vtt()`, `to_json()` → `save_as_json()`. Stable-whisper 2.19+ renamed these methods. |
| Command parsing | `lambda_cut.py:591` | Added `.split("@", 1)[0]` to strip `@botname` suffix from Telegram commands. |
| Paste in onboard | `lambda_cut.py:925` | Changed `input()` to `sys.stdin.readline()` in Gemini key loop. Prevents newline from leaking into next prompt. |
| HTML escaping | `lambda_cut.py:715` | Moved `html.escape()` before `<b>` tag insertion. Tags were being escaped to `&lt;b&gt;`. |

### Infrastructure

| Change | Details |
|--------|---------|
| Symlink for systemd | `~/lambda_cut_v2` → source dir. Systemd cannot handle spaces in paths. |
| Versioning | 1.0 (original), 2.0 (working), 2.0 - Backup, 2.1 (active) |

---

## 2.0 — Initial Release

| Feature | Details |
|---------|---------|
| 5-phase pipeline | Download → Transcribe → Scripts → Clips → TTS |
| Telegram listener | Full command set: `/run_pipeline`, `/run_phase`, `/skip_phase`, `/set_voice`, `/set_style`, `/config`, `/status`, `/logs`, `/help` |
| Onboard wizard | Interactive setup: dependencies, cookies, API keys, bot token, playlist, service, alias |
| API key rotation | Multiple keys in `gemini_keys.txt`, smart rotation, exponential backoff (15s/30s/60s) on 429 |
| VAAPI encoding | AMD GPU hardware encoding for clip generation |
| Stable-ts transcription | VAD enabled, English forced, word timestamps optional |
| Checkpointing | Existing outputs skipped on re-runs |
| Telegram notifications | Phase completion messages sent to configured chat |
| Shell alias | `lambda_cut` command available from anywhere |
