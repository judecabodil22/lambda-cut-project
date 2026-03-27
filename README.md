# Lambda Cut 2.3

Automated pipeline to convert long-form YouTube streams into shorts with AI-generated scripts and TTS narration.

```
YouTube Playlist → Download → Transcribe → AI Scripts → Video Clips → TTS Audio + Subtitles
     Phase 1         Phase 2      Phase 3      Phase 4       Phase 5
```

Each phase can be run independently or skipped. Checkpointing skips existing outputs.

## ⚠️ Security Notice

**IMPORTANT: Never commit your `.env` file or API keys to the repository!**

The `.gitignore` file is configured to exclude sensitive files. When cloning this repository, you must set up your own configuration files.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/judecabodil22/lambda-cut-project.git
cd lambda-cut-project
```

### 2. Set up configuration

```bash
cp .env.example workflows/.env
```

Edit `workflows/.env` with your settings:
- `PLAYLIST_URL`: Your YouTube playlist URL
- `GEMINI_API_KEY`: Your Google Gemini API key
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (optional)
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (optional)

### 3. Run onboard

```bash
cd workflows
python3 lambda_cut.py onboard
```

### 4. Start the listener

```bash
python3 lambda_cut.py listen
```

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

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/run_pipeline` | Run full pipeline |
| `/run_phase 5` | Run specific phase(s) |
| `/run_phase 2,3` | Run phases 2 and 3 |
| `/skip_phase 1,2` | Skip specific phases |
| `/set_voice Puck` | Change TTS voice |
| `/set_style Say...` | Set style prefix |
| `/set_index 3` | Set playlist index |
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
