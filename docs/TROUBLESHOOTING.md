# Troubleshooting Guide

Common issues and their solutions.

## Telegram Bot Issues

### Bot not responding

1. Check if listener is running:
   ```bash
   systemctl --user status lambda-cut-listener.service
   ```

2. Restart the listener:
   ```
   /restart_listener
   ```

3. Check bot token is correct in `.env`

### "Telegram not configured" error

Run the onboard wizard:
```bash
source venv/bin/activate
python workflows/lambda_cut.py onboard
```

---

## Pipeline Issues

### Phase 2: Transcription fails

- **Error**: `VAD TorchScript error`
- **Solution**: The stable-whisper VAD model failed. The pipeline should automatically fall back to stable-ts.

### Phase 3: Script generation fails

- **Error**: `HTTP 503` or rate limiting
- **Solution**: Wait a few minutes and try again. Multiple API keys are supported - it will rotate to the next key.

### Phase 4: No clips generated

- Check that Phase 2 (transcription) completed successfully
- Ensure there's enough disk space
- Check video has detectable scene changes

### Phase 5: TTS fails

- Verify Gemini API key has TTS quota remaining
- Check voice name is valid

---

## System Issues

### Listener stops unexpectedly

1. Check systemd service status:
   ```bash
   systemctl --user status lambda-cut-listener.service
   ```

2. Enable Restart=always:
   ```bash
   systemctl --user enable lambda-cut-listener.service
   ```

3. Check logs:
   ```
   /debug
   ```

### Out of disk space

Clean up old files:
```
/cleanup
```

Or manually delete:
```bash
rm -rf ~/lambda_cut/shorts/*
rm -rf ~/lambda_cut/streams/*
```

### GPU not detected

For VAAPI hardware encoding:
- Verify GPU is available: `vainfo`
- Install drivers: `sudo pacman -S mesa-vdpau`

---

## Network Issues

### Can't download YouTube videos

- Check internet connection
- Verify YouTube playlist URL is correct
- Try with a different video first
- Check if YouTube is blocked by firewall

---

## Getting Help

1. Check the debug logs: `/debug`
2. Check pipeline status: `/status`
3. Review the CHANGELOG.md for known issues
4. Open an issue on GitHub
