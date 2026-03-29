# Lambda Cut TODO

## Current Priorities

### Immediate
- [x] Full pipeline test (run end-to-end with short video)
- [x] Fix any bugs found during testing
- [x] Add simple status/debug command (replacement for /logs)

### Soon
- [x] Enhance README (badges, quick start)
- [x] Basic installer script
- [x] Add CODE_OF_CONDUCT.md
- [x] Create docs/ folder with troubleshooting guides
- [x] Re-add GitHub Actions (removed due to Node.js deprecation issues)

### Later
- [ ] Web Interface MVP
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
- [x] Added /debug command
- [x] Added /clean_backups command
- [x] Added requirements.txt
- [x] Enhanced docs (TTS voices, configuration)

---

## Future Improvements

### Code Quality

#### 1. Refactor Monolithic lambda_cut.py (1600+ lines)
- **Why:** Single file is hard to maintain, test, and understand
- **Benefit:** Easier debugging, better organization, easier for contributors to work on specific modules
- **Effort:** High
- **Suggested structure:**
  ```
  workflows/
  ├── lambda_cut.py       # Main entry, Telegram handler
  ├── transcribe.py       # Phase 2: Transcription
  ├── scripts.py          # Phase 3: AI Script generation
  ├── clips.py            # Phase 4: Clip extraction
  ├── tts.py             # Phase 5: Text-to-speech
  ├── download.py        # Phase 1: YouTube download
  └── utils.py           # Shared utilities
  ```

#### 2. Add Error Handling
- **Why:** Pipeline crashes on edge cases without graceful recovery
- **Benefit:** More robust, production-ready code
- **Effort:** Medium

#### 3. Add Type Hints
- **Why:** Improves code documentation, catches bugs early
- **Benefit:** Better IDE support, self-documenting code
- **Effort:** Medium

#### 4. Remove Dead Code
- **Why:** Unused imports and variables clutter the codebase
- **Benefit:** Cleaner code, easier to maintain
- **Effort:** Low

---

### Functionality Improvements

#### 5. Configurable Clips Per Hour
- **Why:** Users want control over how many clips are generated; prevents too few or too many clips
- **Benefit:** Flexibility for different content types
- **Effort:** Medium
- **Implementation:** Add `CLIPS_PER_HOUR` env var

#### 6. Skip Phase Persistence
- **Why:** Currently user must set skip preferences each run
- **Benefit:** Better user experience for repeated workflows
- **Effort:** Low

#### 7. More Granular Progress Updates
- **Why:** Users want to know what's happening during long phases (e.g., transcription)
- **Benefit:** Better UX, feels more responsive
- **Effort:** Medium

#### 8. Batch Processing / Queue
- **Why:** Process multiple videos without manual intervention
- **Benefit:** Automation for bulk processing
- **Effort:** High

#### 9. Multiple Language Support
- **Why:** Currently only English; non-English content creators want to use it
- **Benefit:** Larger potential user base
- **Effort:** High

---

### Testing & CI/CD

#### 10. Unit Tests
- **Why:** Catches regressions, ensures reliability
- **Benefit:** Confidence when making changes
- **Effort:** Medium

#### 11. Integration Tests
- **Why:** Test phase workflows end-to-end
- **Benefit:** Ensure all parts work together
- **Effort:** Medium

#### 12. Re-add GitHub Actions (Fixed)
- **Why:** Automated linting and testing on PRs
- **Benefit:** Catches issues before merge
- **Effort:** Low

---

### Polish & Features

#### 13. YouTube Upload (Phase 6)
- **Why:** Users want fully automated pipeline from video to uploaded short
- **Benefit:** Complete automation, one-click workflow
- **Effort:** High

#### 14. Customizable Watermark
- **Why:** Content creators want branding on clips
- **Benefit:** Professional-looking output
- **Effort:** Medium

#### 15. Music/Copyright Detection
- **Why:** Warn users about copyrighted audio before upload issues
- **Benefit:** Prevents YouTube claims/strikes
- **Effort:** Medium

#### 16. Video Templates
- **Why:** Apply consistent intro/outro to all clips
- **Benefit:** Professional branding
- **Effort:** Medium

---

### Documentation

#### 17. Contributor Guide
- **Why:** Helps new developers contribute
- **Benefit:** Easier for others to help improve the project
- **Effort:** Low

#### 18. API Reference
- **Why:** Document all Telegram commands and CLI options
- **Benefit:** Better developer experience
- **Effort:** Low

#### 19. Video Tutorial
- **Why:** Visual learners prefer video walkthroughs
- **Benefit:** Easier onboarding for non-technical users
- **Effort:** Medium

---

## Recommended Priorities

### Quick Wins (Do First)
1. ~~**Remove dead code**~~ - Done (no dead code found)
2. ~~**Re-add GitHub Actions properly**~~ - Done (Python-based CI workflow)
3. ~~**Add contributor guide**~~ - Done (CONTRIBUTING.md)

### High Impact (Do Next)
1. ~~**Configurable clips**~~ - Done (CLIPS_PER_HOUR env + /set_clips command)
2. ~~**Better error handling**~~ - Done (validation in all phases)
3. **YouTube upload** - Manual upload preferred (see below)
4. ~~**System keychain**~~ - Done (API keys stored securely in OS keychain)

### YouTube Upload (Manual)
- Phase 6 OAuth implementation removed
- Manual upload via YouTube web UI preferred
- Shorts saved to `shorts/` folder for manual upload

### Long Term (Later)
1. **Refactor into modules** - Improves maintainability
2. **Add tests** - Ensures reliability
3. **Multiple language support** - Expands user base

---

## Recent Updates (March 2026)

- **v2.6.0 Release:**
  - Full pipeline tested end-to-end (10 clips + TTS generated)
  - Security: Removed exposed API keys from git history
  - Telegram fix: HTML parsing error fixed (release notes now escaped with html.escape())
  - Systemd reliability: Changed Restart=on-failure to Restart=always, added network wait
  - Commands: Added /debug (log viewer), /clean_backups; removed broken /logs, /clear_logs
  - Installer: Created install.sh script
  - Requirements: Created requirements.txt
  - Documentation: Enhanced README (badges, quick start), added TTS voices reference, troubleshooting guides, CONFIGURATION.md
  - Added CODE_OF_CONDUCT.md

---

**Status:** v2.6.0 released, ready for showcase
