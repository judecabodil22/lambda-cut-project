# Lambda Cut TODO

## Current Priorities

### Immediate
- [ ] Full pipeline test (run end-to-end with short video)
- [ ] Fix any bugs found during testing
- [ ] Add simple status/debug command (replacement for /logs)

### Soon
- [ ] Enhance README (badges, quick start)
- [ ] Basic installer script
- [ ] Add CODE_OF_CONDUCT.md
- [ ] Create docs/ folder with troubleshooting guides

### Later
- [ ] Web Interface MVP
- [ ] CI/CD setup (GitHub Actions)
- [ ] Packaging (pyproject.toml)
- [ ] GitHub templates (issues, PRs)
- [ ] Contributor guide

---

## Features Implemented

### Pipeline (5 Phases)
- [x] Phase 1: Download (YouTube)
- [x] Phase 2: Transcribe (stable-ts)
- [x] Phase 3: Scripts (Gemini AI)
- [x] Phase 4: Clips (scene-based extraction)
- [x] Phase 5: TTS (Gemini TTS)

### System
- [x] Telegram bot controls
- [x] Auto-update system
- [x] Systemd service (Restart=always)
- [x] Local recording processing

### Completed Fixes
- [x] Security: Removed exposed API keys from git history
- [x] Telegram: HTML parsing fix
- [x] Documentation: Hardcoded paths fixed
- [x] Systemd: Restart=always for foolproof listener

---

## Recent Updates (March 2026)

- **Security fixes:** Removed exposed API keys from git history, cleaned git history
- **Telegram fix:** HTML parsing error fixed (release notes now escaped)
- **Documentation:** Hardcoded paths replaced with ~/ or configurable options
- **Systemd reliability:** Changed Restart=on-failure to Restart=always
- **Removed:** /logs and /clear_logs commands (caused errors)

---

**Status:** Testing and bug fixing phase
