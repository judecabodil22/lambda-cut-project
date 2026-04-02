# Lambda Cut 3.0.1

[![Version](https://img.shields.io/badge/version-3.0.1-blue.svg)](./VERSION)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-purple.svg)](https://archlinux.org/)

Automated pipeline that extracts video clips from long-form YouTube streams and generates AI-powered TTS narration scripts, producing all the raw materials you need for creating shorts in video editing software.

```
YouTube Playlist → Download → Transcribe → AI Scripts → Video Clips → TTS Audio + Subtitles
     Phase 1         Phase 2      Phase 3      Phase 4       Phase 5
```

Each phase can be run independently or skipped. Checkpointing skips existing outputs.

> **Note:** Lambda Cut generates the raw materials (clips, audio, subtitles) for your shorts. You'll need to combine them in video editing software like Kdenlive, DaVinci Resolve, or Premiere Pro.

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/judecabodil22/lambda-cut-project.git
cd lambda-cut-project

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your API keys
nano .env

# 4. Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Run the onboarding wizard
python workflows/lambda_cut.py onboard

# 6. Start the Telegram listener
python workflows/lambda_cut.py listen
```

Then use Telegram commands to control the pipeline!

## 📁 What You Get

After running the pipeline, you'll have:

| Folder | Contents | Use |
|--------|----------|-----|
| `shorts/` | Video clips (MP4) | Import into video editor |
| `tts/` | Narration audio (WAV) + subtitles (SRT) | Add to video editor timeline |
| `scripts/` | AI-generated scripts | Use as narration reference |
| `transcripts/` | Full video transcripts | For reference |

**Next step:** Import these files into Kdenlive, DaVinci Resolve, or your preferred video editor to create your final shorts!

## 📋 Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.10+ |
| FFmpeg | For video processing |
| GPU | Optional but recommended (VAAPI for hardware encoding) |
| Telegram Bot | Get from @BotFather |
| Gemini API Key | Get from Google AI Studio |

### Required Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GEMINI_API_KEY=your_gemini_key
PLAYLIST_URL=https://youtube.com/playlist?list=...
```

## ⚠️ Security Notice

**IMPORTANT: Never commit your `.env` file or API keys to the repository!**

The `.gitignore` file is configured to exclude sensitive files. When cloning this repository, you must set up your own configuration files.

For a detailed changelog, see [CHANGELOG.md](./CHANGELOG.md).

For troubleshooting help, see [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md).

## Recent Highlights

- **10 script variants** — Narrative, News Report, Documentary, True Crime, Character POV, True Story, Mystery Recap, Breakdown, Timeline, Moral/Lesson
- **10 perspectives** — Villain's motive, hero's mistake, hidden detail, cost of outcome, turning point, etc.
- **Matching TTS styles** — Each script variant pairs with a specific voice style for natural flow
- **30 voice rotation** — All Gemini voices (male + female) rotate randomly on listener restart
- **Multi-key TTS fallback** — Automatic rotation through multiple API keys on rate limit
- **Faster transcription** — faster-whisper (4x faster) with SRT generation fix
- **200+ word scripts** — Complete, natural flowing narratives (not poetic fragments)
- **Local recording integration** — `/run_local`, `/set_recording_path`, `/source` commands
- **Auto‑update system** — automatic update detection, backup, and rollback
- **OBS recording workflow** — record locally while streaming for maximum quality
- **Telegram bot control** — full command set with status and logging

## Features

### Pipeline Phases

| Phase | Name | Description |
|-------|------|-------------|
| 1 | Download | Download latest video from YouTube (best quality) |
| 2 | Transcribe | Generate transcript with faster-whisper |
| 3 | Scripts | AI-generated scripts via Gemini (10 variants × 10 perspectives = 100 combinations) |
| 4 | Clips | Extract video clips based on scenes with VAAPI encoding |
| 5 | TTS | Generate narration audio + subtitles with 30 voice options |

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
| `/set_game` | Set game title for script context |
| `/set_recording_path` | Change recording directory |
| `/voices` | List available TTS voices by gender |
| `/restart_listener` | Restart listener (rotates voice) |
| `/source` | Show current recording path |
| `/config` | Show settings |
| `/status` | Show listener and pipeline status |
| `/version` | Show current version |
| `/update` | Check for updates |
| `/stop_listener` | Stop the listener |
| `/stop_pipeline` | Stop running pipeline |
| `/logs` | Show recent pipeline logs |
| `/help` | Show help message |

### CLI Commands

```bash
# Always activate the venv first
source venv/bin/activate

python workflows/lambda_cut.py run              # Run full pipeline
python workflows/lambda_cut.py run -phase 2,3   # Run specific phases
python workflows/lambda_cut.py run -index 3     # Download 3rd video
python workflows/lambda_cut.py listen           # Start Telegram bot
python workflows/lambda_cut.py stop             # Stop listener
python workflows/lambda_cut.py update           # Check for updates
python workflows/lambda_cut.py version          # Show version
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
