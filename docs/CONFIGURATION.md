# Configuration Guide

## Environment Variables

All configuration is done via the `.env` file.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | `123456789` |
| `GEMINI_API_KEY` | API key from Google AI Studio | `AIza...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PLAYLIST_URL` | (none) | YouTube playlist to process |
| `TTS_VOICE` | `Vindemiatrix` | Gemini TTS voice name |
| `TTS_STYLE` | (none) | Style instruction for TTS |
| `GAME_TITLE` | (none) | Game title for script context |
| `CLIPS_PER_HOUR` | `5` | Number of clips to generate per hour |
| `PLAYLIST_INDEX` | `1` | Which video to download from playlist |
| `WORKSPACE` | (auto) | Working directory path |
| `RECORDING_PATH` | `~/Videos/Recordings/` | Local recordings folder |

## Telegram Commands

### Pipeline Control

| Command | Description |
|---------|-------------|
| `/run_pipeline` | Run full pipeline |
| `/run_local` | Process local recordings |
| `/run_phase N` | Run specific phase |
| `/skip_phase N` | Skip specific phase |
| `/stop_pipeline` | Stop running pipeline |

### Configuration

| Command | Description |
|---------|-------------|
| `/set_voice` | Change TTS voice |
| `/set_style` | Set TTS style |
| `/voices` | List available TTS voices |
| `/set_game` | Set game title for script context |
| `/set_recording_path` | Set recordings folder |
| `/config` | Show current settings |

### Status & Debug

| Command | Description |
|---------|-------------|
| `/status` | Show listener and pipeline status |
| `/debug` | Show recent log entries |

### Updates

| Command | Description |
|---------|-------------|
| `/update` | Check for updates |
| `/restart_listener` | Restart the listener |

## TTS Voices

Available Gemini TTS voices (default: Vindemiatrix):

### Female Voices

| Voice | Style |
|-------|-------|
| **Aoede** | Breezy and natural |
| **Kore** | Firm and confident |
| **Leda** | Youthful and energetic |
| **Zephyr** | Bright and cheerful |
| **Autonoe** | Bright and optimistic |
| **Callirrhoe** | Easy-going and relaxed |
| **Despina** | Smooth and flowing |
| **Erinome** | Clear and precise |
| **Gacrux** | Mature and experienced |
| **Laomedeia** | Upbeat and lively |
| **Pulcherrima** | Forward and expressive |
| **Sulafat** | Warm and welcoming |
| **Vindemiatrix** | Gentle and kind |
| **Achernar** | Soft and gentle |

### Male Voices

| Voice | Style |
|-------|-------|
| **Puck** | Upbeat and energetic |
| **Charon** | Informative and clear |
| **Fenrir** | Excitable and dynamic |
| **Orus** | Firm and decisive |
| **Achird** | Friendly and approachable |
| **Algenib** | Gravelly texture |
| **Algieba** | Smooth and pleasant |
| **Alnilam** | Firm and strong |
| **Enceladus** | Breathy and soft |
| **Iapetus** | Clear and articulate |
| **Rasalgethi** | Informative and professional |
| **Sadachbia** | Lively and animated |
| **Sadaltager** | Knowledgeable and authoritative |
| **Schedar** | Even and balanced |
| **Umbriel** | Easy-going and calm |
| **Zubenelgenubi** | Casual and conversational |

### Style Instructions

You can also set a style instruction to customize how the TTS speaks:

```
/set_style Speak in a thoughtful, soft-spoken manner with genuine warmth
```

Or use bracket tags for quick styling:
```
[thoughtful][soft][genuine]
```

## Directory Structure

```
lambda_cut/
├── .env              # Configuration (not in git)
├── workflows/        # Python code
├── streams/         # Downloaded videos
├── transcripts/     # Generated transcripts
├── scripts/         # AI-generated scripts
├── shorts/          # Final video clips
└── tts/            # Generated audio + subtitles
```

## Systemd Service

To run listener as a systemd service:

```bash
# Enable auto-start on boot
systemctl --user enable lambda-cut-listener.service

# Start manually
systemctl --user start lambda-cut-listener.service

# Check status
systemctl --user status lambda-cut-listener.service
```

## API Keys

### Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GEMINI_API_KEY=your_key`

For multiple keys (rate limiting), add to `gemini_keys.txt` (one per line).

### Telegram Bot

1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow prompts to create bot
4. Copy the token to `.env`
5. Get your chat ID: message @userinfobot
