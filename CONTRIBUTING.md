# Contributing to Lambda Cut

Thank you for your interest in contributing!

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/lambda-cut.git`
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run linting: `ruff check workflows/`
6. Commit and push
7. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.12+
- ffmpeg
- yt-dlp
- stable-ts

### Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install ruff
```

### Run Locally

```bash
# Activate venv first
source venv/bin/activate

# Run the pipeline
python workflows/lambda_cut.py run

# Start Telegram listener
python workflows/lambda_cut.py listen

# Run onboarding
python workflows/lambda_cut.py onboard
```

## Code Style

- Follow existing code patterns
- Use ruff for linting: `ruff check workflows/`
- Keep lines under 150 characters when practical
- Add type hints where beneficial

## Project Structure

```
lambda-cut/
├── workflows/
│   ├── lambda_cut.py      # Main entry point
│   └── update_manager.py # Auto-update system
├── docs/                  # Documentation
├── .github/workflows/     # CI/CD
└── ...
```

## Pull Request Process

1. Update documentation if needed
2. Add concise commit message
3. Ensure CI passes
4. Request review

## Reporting Issues

Include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Logs if relevant
