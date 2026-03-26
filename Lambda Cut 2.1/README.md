# Lambda Cut 2.2

Automated pipeline to convert long-form YouTube streams into shorts with AI-generated scripts and TTS narration.

```
YouTube Playlist → Download → Transcribe → AI Scripts → Video Clips → TTS Audio + Subtitles
     Phase 1         Phase 2      Phase 3      Phase 4       Phase 5
```

Each phase can be run independently or skipped. Checkpointing skips existing outputs.

## What's New in 2.2

- **Listener auto-management** — starting a new listener automatically stops any existing one
- **Systemd auto-update** — listener automatically updates systemd service to point to its installation directory
- **Listener status in /status** — shows listener running status, PID, and working directory
- **Logs include timestamps** — `/logs` output now includes date and time for each entry
- **Highest quality download** — downloads best available quality (4K/8K) instead of limiting to 1440p
- **High quality clips** — Phase 4 VAAPI fixed to use proper quality settings (`-rc_mode CQP -global_quality 10 -compression_level 1`). CPU fallback improved to CRF 18
- **Kdenlive automation** — new script generates Kdenlive project files with guides, 4kFX effects, random transitions, and synced subtitles

## What's New in 2.1

- **Telegram is now optional** — skip it during onboard if you don't need notifications
- **Non-blocking pipeline** — Telegram commands work while the pipeline is running (pipeline runs in a background thread)
- **Beautified `/logs`** — emoji status markers, bold phase labels, noise filtered out
- **Fixed Whisper API** — compatible with `stable-whisper` 2.19+ (`to_srt_vtt`, `save_as_json`)
- **Voice selection UI** — numbered list picker during onboard instead of free-text input

## Setup

```bash
python3 workflows/lambda_cut.py onboard
```

The wizard will:
1. Ask where to install (default: `~/lambda_cut/`)
2. Create the workspace directory structure
3. Check dependencies (python3, ffmpeg, yt-dlp, stable-ts, curl)
4. Verify Chrome has YouTube cookies
5. Prompt for your Gemini API key and playlist URL
6. Ask if you want to use Telegram notifications (optional)
7. If yes, prompt for bot token and chat ID with setup instructions
8. Let you pick a TTS voice from a numbered list
9. Validate each input and test all connections
10. Optionally set up Telegram listener as a background service
11. Optionally create a shell alias so you can run `lambda_cut` from anywhere

### What You Need

| Item | Required | Where to Get It |
|------|----------|-----------------|
| Gemini API key | Yes | [Google AI Studio](https://aistudio.google.com/apikey) |
| YouTube playlist | Yes | Your channel's uploads URL |
| Chrome logged into YouTube | Yes | Browser on this machine |
| Telegram bot token | No | [@BotFather](https://t.me/BotFather) |
| Telegram chat ID | No | [@userinfobot](https://t.me/userinfobot) |

## Usage

If alias is set up:
```bash
lambda_cut run
lambda_cut run -phase 2,3
lambda_cut run -index 3
lambda_cut run -skip-phase-1 -skip-phase-2
lambda_cut listen
lambda_cut stop
lambda_cut stop --pipeline
lambda_cut delete-partial
lambda_cut cleanup
lambda_cut clear-logs
lambda_cut onboard
```

Or with full path:
```bash
python3 ~/lambda_cut/workflows/lambda_cut.py run
```

## Telegram Commands

Start the listener (`python3 workflows/lambda_cut.py listen`), then message your bot:

| Command | Description |
|---------|-------------|
| `/run_pipeline` | Run full pipeline (non-blocking) |
| `/run_phase 5` | Run specific phase(s) |
| `/skip_phase 1,2` | Skip specific phases |
| `/set_voice Puck` | Change TTS voice |
| `/set_style Say dramatically:` | Set style prefix |
| `/set_style` | Clear style |
| `/set_index 3` | Set playlist index (1=first video) |
| `/config` | Settings and file counts |
| `/status` | Listener and pipeline status |
| `/logs` | Beautified pipeline logs |
| `/stop_listener` | Stop the listener |
| `/stop_pipeline` | Stop the running pipeline |
| `/delete_partial` | Delete incomplete files |
| `/cleanup` | Delete all generated files |
| `/clear_logs` | Clear pipeline logs |
| `/help` | List all commands |

All commands work while the pipeline is running since it executes in a background thread.

## Pipeline Phases

### Phase 1 — Video Download
Downloads latest video via `yt-dlp` with `--cookies-from-browser chrome`. Retries 3x.

**Output:** `streams/*.webm`

### Phase 2 — Transcription
`stable-ts` with VAD, English forced, garbage cleaning.

**Output:** `transcripts/*.json`, `transcripts/*.srt`

### Phase 3 — Script Generation
Gemini 2.5 Flash-Lite generates first-person scripts with quotes and cliffhangers. Key rotation + rate limiting.

**Output:** `scripts/script_001.txt`, `script_002.txt`, ...

### Phase 4 — Clip Generation
Scene-based extraction via smart dialogue scoring. VAAPI (AMD GPU) or CPU encoding. Loudnorm.

**VAAPI Settings (AMD GPU):** `-rc_mode CQP -global_quality 10 -compression_level 1`
**CPU Settings (Fallback):** `-preset slow -crf 18 -profile:v high -level 4.2 -pix_fmt yuv420p`

**Output:** `shorts/short_001_1.mp4`, `short_001_2.mp4`, ...

### Phase 5 — TTS Generation
Gemini TTS → PCM → WAV (44.1kHz stereo) → SRT subtitles via stable-ts.

**Output:** `tts/tts_001.wav`, `tts_001.srt`, ...

## Configuration

### Environment Variables

Set in `.env` at the workspace root (generated by onboard):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Gemini API key |
| `PLAYLIST_URL` | required | YouTube playlist URL |
| `TELEGRAM_BOT_TOKEN` | optional | Telegram bot token |
| `TELEGRAM_CHAT_ID` | optional | Telegram chat ID |
| `TTS_VOICE` | Algenib | Voice name |
| `TTS_STYLE` | (empty) | Style prefix |
| `SCRIPT_DELAY` | 300 | Seconds between script generations |
| `TTS_DELAY` | 300 | Seconds between TTS generations |

### API Key Rotation

Multiple keys in `gemini_keys.txt` (one per line). Smart rotation across hours. Exponential backoff on 429s (15s, 30s, 60s). Falls back to raw transcript if all keys fail.

### TTS Voices

Achernar, Achird, Algenib, Algieba, Alnilam, Aoede, Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Pulcherrima, Puck, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi.

## Directory Structure

```
Lambda Cut 2.1/
├── streams/                  # Downloaded videos
├── transcripts/              # JSON + SRT transcripts
├── scripts/                  # AI-generated scripts
├── tts/                      # TTS audio + SRT subtitles
├── shorts/                   # Video clips
├── workflows/
│   └── lambda_cut.py         # Single entry point
├── .env                      # Config (private)
├── gemini_keys.txt           # API keys (private)
└── pipeline.log              # Runtime log
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Chrome cookies not working | Chrome is running | Close Chrome first |
| Gemini 429 rate limit | Quota exceeded | Add keys, increase delays |
| Telegram not responding | Listener not running | Run `lambda_cut listen` or enable the service |
| Transcription empty | No speech in video | Check video content |
| Download fails | YouTube rate limit | Pipeline retries 3x; update `yt-dlp` |
| Whisper `to_srt` error | Outdated `stable-whisper` | `pip install stable-ts --upgrade` |

## Changelog

### 2.1

#### Configuration & Setup
- **Telegram is now optional.** Onboard asks "Use Telegram notifications? [y/N]". If no, Telegram fields are omitted from `.env` entirely. The listener command exits with a clear message if Telegram wasn't configured.
- **Config guard added.** `lambda_cut run` refuses to execute if `GEMINI_API_KEY` or `PLAYLIST_URL` is missing or empty from `.env`. Telegram credentials are not required.
- **Workspace detection updated.** `_find_workspace()` resolves from the script's own directory (reads `WORKSPACE=` from `.env` next to the script). Removed `~/lambda_cut` as hardcoded fallback — the workspace location now follows wherever the project is installed.
- **Onboard voice selection changed to numbered list.** Instead of typing a voice name, users pick from a numbered list of all 30 Gemini TTS voices. Current/default voice is highlighted.
- **Gemini API key prompt clarified.** Now reads "Primary Gemini API Key (used for TTS; more keys added below)" so users understand this is one key and more can be added.
- **Telegram setup instructions added.** When user opts into Telegram, onboard prints step-by-step instructions for getting the bot token (via @BotFather) and chat ID (via @userinfobot) before prompting for each value.

#### Pipeline & Listener
- **Pipeline runs in a background thread.** All Telegram commands that trigger the pipeline (`/run_pipeline`, `/run_phase`, `/skip_phase`) now run `run_pipeline()` in a `threading.Thread(daemon=True)`. The listener stays responsive — `/status`, `/logs`, `/config`, and all other commands work while the pipeline is running.
- **Pipeline running flag added.** New global `PIPELINE_RUNNING` (bool) is set `True` when a pipeline starts and `False` when it finishes (including on error, via `finally`). Used by `/status` and `/config` instead of `pgrep`.
- **`/status` simplified.** Removed `pgrep -f "lambda_cut.py run"` check. Now uses `PIPELINE_RUNNING` flag and reads `/tmp/pipeline_status` for the last known phase message.
- **`/config` simplified.** Removed dead `psutil` import and `pgrep` check. Uses `PIPELINE_RUNNING` flag for status.
- **`/logs` beautified.** Filters raw log lines: keeps only timestamped `log()` entries, discards yt-dlp/ffmpeg subprocess noise. Strips timestamps. Adds emoji prefixes (✅ complete, ❌ error, ⏳ in-progress, ⏭️ skipped, • info). Bolds phase labels (`<b>Phase 1:</b>`). Shortens file paths to basename only. Sent as HTML-formatted Telegram message.

#### Bug Fixes
- **Fixed Whisper API for stable-whisper 2.19+.** `WhisperResult.to_srt()` renamed to `to_srt_vtt()`. `WhisperResult.to_json()` renamed to `save_as_json()`. Updated all 3 call sites (Phase 2 transcription, Phase 5 TTS SRT generation).
- **Fixed Telegram command parsing with bot username suffix.** Commands like `/help@sophia_blackmesa_bot` were not matching because the parser compared the full string. Added `.split("@", 1)[0]` to strip the `@botname` suffix before matching.
- **Fixed paste issue in onboard key loop.** Pasting a Gemini API key with Ctrl+Shift+V caused a trailing newline to leak into the next `input()` call, making it immediately empty and breaking the loop. Changed from `input()` to `sys.stdin.readline()` which properly consumes pasted newlines.
- **Fixed HTML escaping in beautified logs.** `html.escape()` was applied after adding `<b>` tags, which escaped them to `&lt;b&gt;`. Moved escape before HTML formatting so bold tags survive.

#### Infrastructure
- **Symlink for systemd.** Created `~/lambda_cut_v2` → source directory because systemd cannot handle spaces in `ExecStart`/`WorkingDirectory` paths.
- **Project versioned.** Lambda Cut 1.0 (original), 2.0 (working copy), 2.0 - Backup, 2.1 (active).

### 2.0
- Initial release with 5-phase pipeline (Download → Transcribe → Scripts → Clips → TTS)
- Telegram bot listener with full command set
- Interactive onboard wizard with dependency checking and connection verification
- Gemini API key rotation across hours with exponential backoff on 429s
- VAAPI (AMD GPU) hardware encoding for clip generation
- `stable-ts` transcription with VAD and English language forcing
- Checkpointing — existing outputs are skipped on re-runs
- Telegram notifications for phase completions
- Shell alias setup for `lambda_cut` command
