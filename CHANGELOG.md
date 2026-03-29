# Lambda Cut Changelog

All notable changes to this project documented here.

## 2.6.0 — 2026-03-29

### New Features

| Change | Details |
|--------|---------|
| Added /debug command | Simple debug log viewer to replace /logs functionality |
| Added /clean_backups command | Clean old backup versions via Telegram |
| Added requirements.txt | Documented Python dependencies |
| Added GitHub Actions | Auto-lint on PRs |
| Enhanced docs | Added TTS voices reference, clarified output |

### Improvements

| Change | Details |
|--------|---------|
| Fixed LSP type errors | Added type ignore comments for stable_whisper |
| Transcription checkpointing | Already exists - skips if transcript exists |

---

## 2.5.21 — 2026-03-29

### Bug Fixes & Improvements

| Change | Details |
|--------|---------|
| Added /debug command | Simple debug log viewer to replace /logs functionality |

---

## 2.5.20 — 2026-03-29

### Bug Fixes & Improvements

| Change | Details |
|--------|---------|
| Telegram HTML parsing | Fixed by escaping release_notes with html.escape() to prevent parse errors |
| Removed /logs command | Command removed due to persistent errors from log noise |
| Removed /clear_logs command | Command removed (no longer needed without /logs) |
| Systemd service reliability | Changed Restart=on-failure to Restart=always, added network wait delay |

---

## 2.5.19 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Telegram HTTP 400 errors | Fixed by changing default parse_mode from HTML to plain text and improving error logging |
| Stable-ts command updated | Updated TTS SRT generation to use explicit output file and proper parameters |
| VAD TorchScript error handling | Added fallback from stable-whisper to stable-ts when model fails |
| HTML tags in SRT files | Ensured word_level is false to avoid HTML tags in output |

---

## 2.5.18 — 2026-03-28

### Phase 6 Removed

| Change | Details |
|--------|---------|
| Phase 6 removed | Kdenlive automation disabled due to persistent XML parsing issues |
| Rationale | The complex template-based approach proved too fragile to maintain |

---

## 2.5.17 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Kdenlive crash | Fixed by properly removing playlist entries referencing removed chains |

---

## 2.5.16 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Kdenlive crash | Fixed by removing orphaned playlist entries that reference removed chains |

---

## 2.5.15 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| SRT generation | Use stable-ts CLI with --output_format srt (clean output without HTML tags) |

---

## 2.5.14 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| stable-ts command | Fixed argument order: `--word_level false --device cpu --language en` |

---

## 2.5.13 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| stable-ts command | Updated stable-ts CLI command: `--word_level false --language en --device cpu` |

---

## 2.5.12 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| stable-ts command | Fixed stable-ts CLI command for SRT generation |

---

## 2.5.11 — 2026-03-28

### Features

| Feature | Details |
|---------|---------|
| Kdenlive templates | Base template now in templates/ folder instead of output/ |

---

## 2.5.10 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Kdenlive markers | Fixed markers now use script titles from workspace |

---

## 2.5.9 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Kdenlive crash | Fixed crash by removing references to non-existent TTS/shorts files |

---

## 2.5.8 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Kdenlive paths | Fixed hardcoded source directory paths in Kdenlive project generation |

---

## 2.5.7 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Restart flag reset | Reset LISTENER_RESTART flag after triggering restart to prevent spam |
| Global declaration | Fixed syntax error with global declaration in listen() |

---

## 2.5.6 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Restart mechanism | Changed from os.execv to subprocess.Popen with new session for reliable restart |

---

## 2.5.5 — 2026-03-28

### Features

| Feature | Details |
|---------|---------|
| `/restart_listener` command | Restart listener via Telegram (same mechanism as update restart) |
| systemd `Restart=always` | Listener auto-restarts after any exit (crash, stop, or restart) |

### Bug Fixes

| Fix | Details |
|-----|---------|
| Listener restart | Fixed restart by waiting for update thread to complete before checking flag |

---

## 2.5.4 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Listener restart | Fixed restart by waiting for update thread to complete before checking flag |

---

## 2.5.3 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Listener restart | Fixed restart by moving os.execv from daemon thread to main polling loop |

---

## 2.5.2 — 2026-03-28

### Bug Fixes

| Fix | Details |
|-----|---------|
| Update target path | Fixed `script_root` to use project root instead of `workflows/` subdirectory |
| Listener restart | Fixed `os.execv` call to work reliably with 1-second delay |
| Help text | Added `/run_local` command to help display |

### New Features

| Feature | Details |
|---------|---------|
| `/run_local` command | Process local recordings instead of YouTube |
| Recording support | Supports .mp4, .mkv, .webm, .avi, .mov formats |
| Pipeline integration | Full pipeline runs on local recordings |

---

## 2.5.1 — 2026-03-28

### Update System Fix

| Fix | Details |
|-----|---------|
| Directory structure | Fixed nested directory creation during updates |
| File copying | Corrected to preserve installed directory structure |
| Backup validation | Improved backup verification |
| QA testing | Added testing checklist for new features |

### Update & Restart Bug Fixes

| Fix | Details |
|-----|---------|
| Update target path | Fixed `script_root` to use project root instead of `workflows/` subdirectory |
| Listener restart | Fixed `os.execv` call to work from update thread for reliable restarts |
| Help text | Added `/run_local` command to help display |

### QA Process Added

- All new features must undergo testing before deployment
- Test checklist includes: basic functionality, edge cases, integration
- Update system now tested with directory structure preservation

---

## 2.5 — 2026-03-27

### Local Recording Integration

| Feature | Details |
|---------|---------|
| `/run_local` command | Process local recordings instead of YouTube (one-time override) |
| `/set_recording_path` | Change recording directory |
| `/source` | Show current recording path |
| Default behavior | YouTube playlist remains default |
| File formats | Supports .mp4, .mkv, .webm |
| Sorting | Oldest first (chronological) |
| Delay | 300 seconds between videos |

---

## 2.4 — 2026-03-27

### OBS Recording Workflow (Planned)

| Feature | Details |
|---------|---------|
| Recording path | `~/Videos/Recordings/` (configurable) |
| Recording format | Fragmented MP4 (crash recovery) |
| Recording quality | CQP 16 (visually lossless) |
| Recording resolution | 1440p @ 60fps |
| Auto-detection | Lambda Cut will auto-detect new recordings |
| Integration | Uses local recording instead of YouTube VOD |

### Optimal Settings Documented

| Setting | Value | Reason |
|---------|-------|--------|
| **Streaming** | 1440p @ 60fps, 24 Mbps CBR | YouTube optimal for 1440p |
| **Recording** | 1440p @ 60fps, CQP 16 | High quality for Lambda Cut |
| **File format** | Fragmented MP4 | Crash recovery for long streams |
| **Encoder** | VAAPI H.264 | GPU encoding, low CPU usage |

### Planned Integration

- Lambda Cut will watch `~/Videos/Recordings/` for new files
- Auto-select latest recording for processing
- No manual file selection needed
- Skip YouTube VOD download (use local recording)

---

## 2.3 — 2026-03-27

### Auto-Update System

| Feature | Details |
|---------|---------|
| Update detection | Checks for updates on listener startup, every 24 hours, and on `/status` |
| GitHub integration | Hybrid approach: VERSION file check (no API) + release notes (on-demand) |
| Backup system | Automatic backup before update (keeps up to 2 previous versions) |
| Rollback support | Backups stored in `/backups` directory for manual restore |
| `/update` command | Check for and install updates via Telegram |
| `/version` command | Show current version and update status |
| `/confirm_update` | Confirm update after reviewing release notes |
| `/status` enhanced | Now shows version and update availability |
| CLI update | `lambda_cut update` command |

### Security

| Feature | Details |
|---------|---------|
| HTTPS only | All downloads use HTTPS |
| No credentials | No API tokens stored |
| Official source | Downloads only from GitHub |
| Backup before update | Rollback if something goes wrong |

---

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
