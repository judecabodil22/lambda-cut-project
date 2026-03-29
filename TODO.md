# Lambda Cut Open-Source Launch TODO

## Phase 1: Repository Polish (Week 1)
- [x] Security sweep: Ensure no API keys in history, validate `.gitignore`
- [ ] Enhance README: Add badges, GIF demo, installation comparison table
- [ ] Create `docs/` directory with detailed guides (troubleshooting, configuration)
- [ ] GitHub templates: Issue/PR templates, `CONTRIBUTING.md`
- [ ] Demo video: 2-minute showcase (record with OBS)

## Phase 2: Installation Simplification (Week 1)
- [ ] Create one-click installer script (bash/python)
  - Checks Python 3.8+, ffmpeg, system dependencies
  - Creates virtual environment
  - Installs requirements
  - Runs onboarding wizard
- [ ] Add "Quick Start" section to README
  - Three-line install command
  - Prerequisites table
  - First-run example with expected output
- [ ] Add minimal tests for core functions (version comparison, script parsing)
- [ ] Set up GitHub Actions for CI (linting, basic tests)

## Phase 3: Packaging & Distribution (Week 2)
- [ ] Convert to proper Python package with `pyproject.toml`
- [ ] Define CLI entry point (`lambda-cut` command)
- [ ] Platform-specific installation guides (Windows/macOS/Linux)
- [ ] Optional: Homebrew tap for macOS users

## Phase 4: Web Interface MVP (Weeks 3-4)
- [ ] Choose framework: Flask + Bootstrap or Streamlit
- [ ] Core features: Configuration editor, pipeline monitor, log viewer
- [ ] Integration: Call existing CLI commands under the hood
- [ ] Package as `lambda-cut-web` optional extra

## Phase 5: Marketing Launch (Week 5)
- [ ] Blog post on dev.to/Medium about automating YouTube shorts
- [ ] Reddit posts (r/Python, r/selfhosted, r/streaming, r/YouTubers)
- [ ] Hacker News "Show HN" post
- [ ] Create Discord server for support and community
- [ ] GitHub release v3.0.0 with all changes

## Phase 6: Sustained Growth (Ongoing)
- [ ] Regular monthly releases, respond to issues promptly
- [ ] Contributor guide with "good first issue" labels
- [ ] Showcase user stories, feature users who share their shorts
- [ ] Potential extensions: OBS plugin, mobile companion app

## Innovative Features to Highlight
- [ ] 5-phase pipeline (Download → Transcribe → AI Scripts → Clips → TTS)
- [ ] OBS local recording integration for maximum quality
- [ ] Telegram bot control with full command set
- [ ] Auto-update system with backup and rollback
- [ ] Multi-GPU support (VAAPI) with CPU fallback
- [ ] Configurable AI scripts via Gemini API

## Documentation Needs
- [ ] Architecture diagram
- [ ] API reference for Telegram commands
- [ ] Troubleshooting common issues
- [ ] Configuration options explained
- [ ] Example workflows (gaming streams, podcasts, tutorials)

## Testing Goals
- [ ] Unit tests for core modules
- [ ] Integration tests for pipeline phases
- [ ] End-to-end test with sample video
- [ ] Performance benchmarks

## Community Building
- [ ] Set up GitHub Discussions
- [ ] Create issue labels (bug, enhancement, documentation)
- [ ] Write CODE_OF_CONDUCT.md
- [ ] Add license (current is MIT, ensure it's correct)

## Success Metrics
- [ ] GitHub stars goal: 100 in first month
- [ ] User testimonials
- [ ] Contributor count
- [ ] YouTube tutorial views

---

## Recent Updates (March 2026)

- **Security fixes:** Removed exposed API keys from git history, cleaned git history
- **Telegram fix:** HTML parsing error fixed (release notes now escaped)
- **Documentation:** Hardcoded paths replaced with ~/ or configurable options
- **Pipeline:** Phase 6 (Kdenlive) removed from documentation and code

**Current Status:** Phase 1 in progress - repository polish
**Next Immediate Actions:** Continue with Phase 1 (enhance README, create docs/, GitHub templates)
