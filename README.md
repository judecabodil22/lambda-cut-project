# Lambda Cut 2.5.2

Automated pipeline to convert long-form YouTube streams into shorts with AI-generated scripts and TTS narration.

```
YouTube Playlist → Download → Transcribe → AI Scripts → Video Clips → TTS Audio + Subtitles → Kdenlive Project
     Phase 1         Phase 2      Phase 3      Phase 4       Phase 5                         Phase 6
```

Each phase can be run independently or skipped. Checkpointing skips existing outputs.

## ⚠️ Security Notice

**IMPORTANT: Never commit your `.env` file or API keys to the repository!**

The `.gitignore` file is configured to exclude sensitive files. When cloning this repository, you must set up your own configuration files.

## What's New in 2.5.2

- **Update path fix** — updates now correctly target project root instead of `workflows/` subdirectory
- **Restart fix** — listener reliably restarts after update
- **`/run_local` command** — process local recordings instead of YouTube

## What's New in 2.5.1

- **Update system fix** — fixed directory structure issue during updates
- **QA process** — all new features must be tested before deployment

## What's New in 2.5

- **Phase 6: Kdenlive project creation** — auto-generates Kdenlive project with all assets ready for rendering
- **`/run_local` command** — process local recordings instead of YouTube (one-time override)
- **`/set_recording_path`** — change recording directory
- **`/source`** — show current recording path
- **Auto Phase 6** — runs automatically after Phase 5

## What's New in 2.4

- **OBS recording workflow** — record locally while streaming for maximum quality
- **Optimal settings documented** — streaming and recording settings for 1440p
- **Fragmented MP4 format** — crash recovery for long streams

## What's New in 2.3

- **Auto-update system** — automatic update detection and installation from GitHub
- **Backup system** — automatic backup before update (keeps up to 2 previous versions)
- **Release notes** — view release notes before updating
- **`/update` command** — check for and install updates via Telegram
- **`/version` command** — show current version and update status
- **`/status` enhanced** — now shows version and update availability

## What's New in 2.2

- **Listener auto-management** — starting a new listener automatically stops any existing one
- **Systemd auto-update** — listener automatically updates systemd service to point to its installation directory
- **Listener status in /status** — shows listener running status, PID, and working directory
- **Logs include timestamps** — `/logs` output now includes date and time for each entry
- **Highest quality download** — downloads best available quality (4K/8K) instead of limiting to 1440p
- **High quality clips** — Phase 4 VAAPI fixed to use proper quality settings (`-rc_mode CQP -global_quality 10 -compression_level 1`). CPU fallback improved to CRF 18

## Features

### Pipeline Phases

| Phase | Name | Description |
|-------|------|-------------|
| 1 | Download | Download latest video from YouTube (best quality) |
| 2 | Transcribe | Generate transcript with stable-ts |
| 3 | Scripts | AI-generated short scripts via Gemini |
| 4 | Clips | Extract video clips based on scenes |
| 5 | TTS | Generate narration audio + subtitles |
| 6 | Kdenlive | Auto-generate Kdenlive project with all assets |

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/run_pipeline` | Run full pipeline from YouTube |
| `/run_local` | Process local recordings (one-time override) |
| `/run_phase 5` | Run specific phase(s) |
| `/run_phase 2,3` | Run phases 2 and 3 |
| `/skip_phase 1,2` | Skip specific phases |
| `/set_voice Puck` | Change TTS voice |
| `/set_style Say...` | Set style prefix |
| `/set_index 3` | Set playlist index |
| `/set_recording_path` | Change recording directory |
| `/source` | Show current recording path |
| `/config` | Show settings |
| `/status` | Show listener and pipeline status |
| `/version` | Show current version |
| `/update` | Check for updates |
| `/stop_listener` | Stop the listener |
| `/stop_pipeline` | Stop running pipeline |
| `/logs` | Show pipeline logs |

### CLI Commands

```bash
python3 lambda_cut.py run              # Run full pipeline
python3 lambda_cut.py run -phase 2,3   # Run specific phases
python3 lambda_cut.py run -index 3     # Download 3rd video
python3 lambda_cut.py listen           # Start Telegram bot
python3 lambda_cut.py stop             # Stop listener
python3 lambda_cut.py update           # Check for updates
python3 lambda_cut.py version          # Show version
```

## Update System

Lambda Cut includes an automatic update system:

- Checks for updates on listener startup
- Checks for updates every 24 hours
- Shows update status in `/status`
- `/update` command to install updates
- Automatic backup before update (up to 2 backups)

## OBS Recording Workflow (Optimal Quality)

For maximum quality, record locally while streaming. This provides higher quality source material for Lambda Cut processing.

### Recommended OBS Settings

#### Streaming Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Resolution | 2560x1440 (1440p) | Optimal for 1080p game |
| Frame Rate | 60 fps | Smooth motion |
| Encoder | FFMPEG VAAPI H.264 | GPU encoding |
| Rate Control | CBR | For streaming |
| Bitrate | 24,000 kbps | YouTube optimal for 1440p |
| Profile | High | Best quality |
| Level | Auto | |
| Keyframe Interval | 2 seconds | |
| Max B-Frames | 2 | |

#### Recording Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Resolution | 2560x1440 (1440p) | Match stream |
| Frame Rate | 60 fps | |
| Encoder | FFMPEG VAAPI H.264 | Same as stream |
| Rate Control | CQP | Best for recording |
| CQP | 16 | Visually lossless |
| Profile | High | |
| Level | Auto | |
| Keyframe Interval | 2 seconds | |
| File Format | Fragmented MP4 | Crash recovery |
| Recording Path | `/home/alph4r1us/Videos/Recordings/` | |

### Why Record Locally?

| Method | Quality | File Size | Compression |
|--------|---------|-----------|-------------|
| YouTube VOD | Compressed | Medium | 3 generations |
| Local Recording | Original | Large | 1 generation |

### Recording Path

```
/home/alph4r1us/Videos/Recordings/
```

Lambda Cut will auto-detect new recordings in this directory.

### Benefits

1. **Higher quality source** — No YouTube re-encoding loss
2. **Faster processing** — No download step
3. **Original quality** — CQP 16 preserves detail
4. **Crash recovery** — Fragmented MP4 protects against crashes

## Project Structure

```
lambda-cut-project/
├── workflows/
│   └── lambda_cut.py         # Main pipeline code
│   └── update_manager.py     # Update logic
├── scripts/                  # Generated AI scripts
├── shorts/                   # Generated video clips
├── tts/                      # Generated TTS audio
├── transcripts/              # Video transcripts
├── streams/                  # Downloaded YouTube videos
├── output/                   # Kdenlive project files
├── backups/                  # Automatic backups
├── .env.example              # Configuration template
├── VERSION                   # Current version
├── CHANGELOG.md              # Version history
└── README.md                 # This file
```

## Support

For issues or questions, create an issue on GitHub:
https://github.com/judecabodil22/lambda-cut-project/issues

## License

See LICENSE file.
