# Lambda Cut

Automated pipeline to convert long-form YouTube streams into shorts with AI-generated scripts and TTS narration.

## Project Structure

| Folder | Description |
|--------|-------------|
| `Lambda Cut 2.1/` | Current active version |
| `Lambda Cut 2.0/` | Previous version |
| `Lambda Cut 2.0 - Backup/` | Backup of version 2.0 |
| `Lambda Cut 1.0/` | Original version |

## Quick Start (Version 2.1)

```bash
cd "Lambda Cut 2.1/workflows"
python3 lambda_cut.py onboard
python3 lambda_cut.py listen
```

## Features

- Download YouTube videos (best quality available - 4K/8K)
- Transcribe with stable-ts
- Generate AI scripts with Gemini (third-person narrative style)
- Extract video clips based on scenes (high quality VAAPI encoding)
- Generate TTS audio with subtitles

## Version

Current: **2.2** (see `Lambda Cut 2.1/` for latest code)

## License

MIT License - see LICENSE file
