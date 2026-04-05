# Lambda Cut Changelog

All notable changes to this project documented here.

## 3.3.0 — 2026-04-05

### New Features

| Feature | Description |
|---------|-------------|
| SRT word wrapping for Phase 5 | TTS SRT files now split long subtitles into 10-word chunks with individual timestamps |
| `/set_srt_words` command | Telegram command to set max words per SRT subtitle (3-20, default: 10) |

### Bug Fixes

| Fix | Details |
|-----|---------|
| SRT word wrapping | Phase 5 TTS now wraps to 10 words per line for better 9:16 video readability |
| Phase 1 SRT cleanup | Removed word wrapping from Phase 1 (pipeline) - only Phase 5 uses it |

### Technical Changes

| Change | Description |
|---------|-------------|
| SRT splitting logic | Long subtitles now split into separate SRT entries with proportional timing |
| Configurable SRT words | Uses SRT_MAX_WORDS from .env (default: 10), configurable via /set_srt_words |

---

## 3.2.1 — 2026-04-03

### Bug Fixes

| Fix | Details |
|-----|---------|
| TTS API format | Fixed Content Studio TTS to use same API format as pipeline |
| Script cleaning | Added script cleaning function to remove production notes before TTS |
| Character relationship hallucination | AI now forbidden from inventing relationships between characters |
| External knowledge | AI forbidden from adding plot details not in transcript |

### New Features

| Feature | Description |
|---------|-------------|
| Script cleaning for TTS | Removes stage directions, visual cues, formatting before TTS |
| Character relationship restrictions | AI must not invent character connections not in transcript |

### Content Studio Improvements

| Improvement | Description |
|-------------|-------------|
| Script cleaning | Before TTS, removes: **(Stage directions)**, **(Visual cues)**, **Bold markers** |
| Word count display | Shows cleaned word count before TTS generation |
| Key plot points enforcement | Script must cover extracted plot points from transcript |

---

## 3.2.0 — 2026-04-03

### New Features

| Feature | Description |
|---------|-------------|
| Content Studio | New feature for generating additional content from existing transcripts |
| `/cs` command | Opens Content Studio menu |
| Import Pipeline Data | Moves all transcripts + shorts from pipeline to content_studio |
| Generate Script | Analyzes ALL transcripts, generates ~1500 word script |
| Generate TTS | Creates TTS audio from existing scripts |
| Auto-detect | AI determines best content type, subject, and voice from transcript |
| Full transcript reading | No truncation - reads entire transcript for better context |
| Key plot points | Analysis extracts specific plot events for accurate script generation |
| Game context | Uses GAME_TITLE from settings for context |

### Content Studio Menu

```
📥 Import Pipeline Data  - Move pipeline transcripts + shorts to content_studio
🎬 Generate Script       - Analyze transcripts, generate script (~1500 words)
🎤 Generate TTS          - Generate TTS from latest script
🗑️ Clear All            - Delete all content_studio files
```

### Technical Improvements

| Improvement | Details |
|-------------|---------|
| Full transcript support | Removed 50k char and 8k char limits - reads entire transcript |
| Real character extraction | AI returns list of actual characters in transcript |
| Key plot points extraction | AI extracts specific plot events for script accuracy |
| Script-only generation | Separated script generation from TTS |
| TTS retry logic | Added retry with exponential backoff for 429/503 errors |
| Game context in prompts | Includes GAME_TITLE setting in analysis and generation |

### Script Accuracy Improvements

| Change | Description |
|--------|-------------|
| Character restrictions | Script must only use characters from transcript |
| Plot point enforcement | Script must cover extracted key plot points |
| External knowledge banned | AI warned not to add story elements not in transcript |
| Show detected info | Telegram shows detected characters and plot points before generation |

### Bug Fixes

| Fix | Details |
|-----|---------|
| Import uses move | Changed from copy to move - files transfer from pipeline |
| TTS retry on 503 | Added retry logic for service unavailable errors |
| Full transcript context | Fixed truncation - now reads all ~42k characters |

### Changes

| Change | Details |
|--------|---------|
| Version bump | 3.2.0 |

---

## 3.1.1 — 2026-04-02

### Bug Fixes

| Fix | Details |
|-----|---------|
| Restart button | Fixed restart button not working - now properly exits and restarts service |

---

## 3.1.0 — 2026-04-02

### New Features

| Change | Details |
|--------|---------|
| Telegram Inline Menu | `/menu` command shows interactive button-based menu |
| Rich Status Cards | Shows file counts, config settings, pipeline status with emoji |
| Interactive Config | Tap buttons to set voice, index, style, game (no commands needed) |
| File Browser | View generated files by category (scripts, clips, TTS) |
| Help Menu | Commands, Phases, Voices reference via inline menu |
| 30 Voices | All 30 Gemini TTS voices selectable from menu |
| 10 Styles | Narrative, Exciting, Mysterious, Funny, etc. |
| 10 Games | Popular games pre-configured (Life is Strange, Spider-Man, etc.) |
| Playlist Index | Quick select 1-10 from menu |
| Cleanup | One-tap cleanup of all generated files |

### Improvements

| Change | Details |
|--------|---------|
| Menu Navigation | Back buttons on all sub-menus |
| Visual Feedback | ✓ shows current selection in menus |
| Error Handling | Better callback errors - shows text even with None response |
| Config Display | Shows current values for voice, index, style, game |
| File Counts | Shows file counts in file browser menu |

### Bug Fixes

| Fix | Details |
|-----|---------|
| Config buttons | Fixed "Unknown action" for index, style, game buttons |
| Menu display | Fixed config sub-menu not showing (was missing response_text) |
| Help button | Fixed help showing nothing |

### New Commands

| Command | Description |
|---------|-------------|
| `/menu` | Show interactive inline menu |

---

## 3.0.1 — 2026-04-02

### New Features

| Change | Details |
|--------|---------|
| 10 script variants | Narrative, News Report, Documentary, True Crime, Character POV, True Story, Mystery Recap, Breakdown, Timeline, Moral/Lesson |
| 10 perspectives | Villain's motive, hero's mistake, hidden detail, cost of outcome, turning point, emotional undercurrent, consequence, mystery, moral dilemma, ripple effect |
| 10 TTS voice styles | Each script variant has a matching TTS voice style |
| 30 voices | All Gemini voices (male + female) rotate randomly on listener restart |
| Multi-key TTS fallback | Rotates through multiple API keys on rate limit (429) |
| Faster transcription | Uses faster-whisper as primary (4x faster) |
| SRT generation fix | Uses faster-whisper instead of broken stable-ts |
| Script word requirement | 200+ words minimum for complete, natural scripts |
| Improved transcript extraction | Minimum 3 words per segment (was 10) |

### Improvements

| Change | Details |
|--------|---------|
| Voice rotation fix | Listener restart now uses systemd to ensure voice rotates properly |
| Voice name fix | Corrected Callirhoe to Callirrhoe for Gemini TTS API |
| TTS retry logic | 5 retries with 60s initial delay and exponential backoff |
| TTS rate limiting | 2 second delay between requests to respect API limits |
| Telegram restart loop fix | Persists update offset to prevent /restart_listener loop |
| Script log | Logs which variant/perspective used for each script |

### Changes

| Change | Details |
|--------|---------|
| Removed Google Cloud TTS | Gemini TTS provides better style support for character voices |
| TTS delay | Reduced from 300s to 120s between scripts |

---

## 2.8.0 — 2026-03-29

### New Features

| Change | Details |
|--------|---------|
| System keychain support | API keys now stored in system keychain instead of plain text files |
| Added keychain_manager.py | New module for secure key storage |
| Keychain storage for Gemini | Multiple API keys stored securely |
| Keychain for Telegram | Bot token and chat ID stored securely |
| Fallback to files | If keychain unavailable, falls back to .env and gemini_keys.txt |

### Improvements

| Change | Details |
|--------|---------|
| Better error handling | Added validation and error handling to all pipeline phases |
| Phase 1 (Download) | Added PLAYLIST_URL and cookies validation, video file check |
| Phase 2 (Transcribe) | Added video file validation, better fallback logging |
| Phase 3 (Scripts) | Added transcript and API keys validation, counts generated scripts |
| Phase 4 (Clips) | Added video/transcript validation, ffmpeg check, duration validation |
| Phase 5 (TTS) | Added voice and API key validation, better error tracking |

### Changes

| Change | Details |
|--------|---------|
| Removed Phase 6 YouTube Upload | Manual upload preferred for more control |
| Removed /upload command | Use YouTube web UI for uploads |

### New Features (retained from 2.7.0)

| Change | Details |
|--------|---------|
| Added GitHub Actions CI | Python-based workflow with ruff linting and syntax check |
| Added CONTRIBUTING.md | Contributor guide for developers |
| Configurable clips per hour | CLIPS_PER_HOUR env var + /set_clips command |

---

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
