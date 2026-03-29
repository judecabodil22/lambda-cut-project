# Lambda Cut 2.5.20

Automated pipeline to convert long-form YouTube streams into shorts with AI-generated scripts and TTS narration.

```
YouTube Playlist → Download → Transcribe → AI Scripts → Video Clips → TTS Audio + Subtitles
     Phase 1         Phase 2      Phase 3      Phase 4       Phase 5
```

Each phase can be run independently or skipped. Checkpointing skips existing outputs.

## ⚠️ Security Notice

**IMPORTANT: Never commit your `.env` file or API keys to the repository!**

The `.gitignore` file is configured to exclude sensitive files. When cloning this repository, you must set up your own configuration files.

For a detailed changelog, see [CHANGELOG.md](./CHANGELOG.md).

## Recent Highlights

- **Local recording integration** — `/run_local`, `/set_recording_path`, `/source` commands for processing local videos
- **Auto‑update system** — automatic update detection, backup, and rollback
- **OBS recording workflow** — record locally while streaming for maximum quality
- **Telegram bot control** — full command set: `/run_pipeline`, `/run_phase`, `/skip_phase`, `/set_voice`, `/set_style`, `/config`, `/status`, `/logs`, and more

## Features

### Pipeline Phases

| Phase | Name | Description |
|-------|------|-------------|
| 1 | Download | Download latest video from YouTube (best quality) |
| 2 | Transcribe | Generate transcript with stable-ts |
| 3 | Scripts | AI-generated short scripts via Gemini |
| 4 | Clips | Extract video clips based on scenes |
| 5 | TTS | Generate narration audio + subtitles |

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
| Recording Path | `~/Videos/Recordings/` (configurable via `/set_recording_path`) | |

### Why Record Locally?

| Method | Quality | File Size | Compression |
|--------|---------|-----------|-------------|
| YouTube VOD | Compressed | Medium | 3 generations |
| Local Recording | Original | Large | 1 generation |

### Recording Path

```
~/Videos/Recordings/
```

Configure via `/set_recording_path` command or `RECORDING_PATH` in `.env`.

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
