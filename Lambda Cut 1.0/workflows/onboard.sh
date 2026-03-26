#!/bin/bash
# onboard.sh — Interactive setup for Lambda Cut
# Run this once to configure the pipeline for your environment.

set -euo pipefail

WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$WORKFLOW_DIR/.env"
KEYS_FILE="$WORKFLOW_DIR/gemini_keys.txt"
PASS="\033[32m✓\033[0m"
FAIL="\033[31m✗\033[0m"
WARN="\033[33m!\033[0m"
BOLD="\033[1m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD} Lambda Cut — Setup${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""

# ─── Dependency Check ─────────────────────────────────────────────────────────

echo -e "${BOLD}Checking dependencies...${RESET}"
MISSING=0

check_dep() {
    local name="$1" cmd="${2:-$1}"
    if command -v "$cmd" &>/dev/null; then
        local ver
        ver=$("$cmd" --version 2>&1 | head -1)
        echo -e "  $PASS $name  $ver"
    else
        echo -e "  $FAIL $name  NOT FOUND"
        MISSING=1
    fi
}

check_dep "python3"
check_dep "ffmpeg"
check_dep "ffprobe"
check_dep "yt-dlp"
check_dep "curl"

# Check stable-ts (python package)
if python3 -c "import stable_whisper" 2>/dev/null; then
    VER=$(python3 -c "import stable_whisper; print(stable_whisper.__version__)" 2>/dev/null || echo "?")
    echo -e "  $PASS stable-ts  v$VER"
else
    echo -e "  $FAIL stable-ts  NOT FOUND  (pip install stable-ts)"
    MISSING=1
fi

if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo -e "  ${FAIL} Install missing dependencies before continuing."
    echo -e "    pip install stable-ts"
    echo -e "    pip install yt-dlp   # or your package manager"
    echo -e "    sudo apt install ffmpeg curl python3"
    exit 1
fi

echo ""

# ─── Cookie Check ─────────────────────────────────────────────────────────────

echo -e "${BOLD}Checking browser cookies...${RESET}"
if yt-dlp --cookies-from-browser chrome -j "https://www.youtube.com/watch?v=dQw4w9WgXcQ" &>/dev/null; then
    echo -e "  $PASS Chrome cookies accessible (YouTube login detected)"
else
    echo -e "  $WARN Chrome cookies not accessible."
    echo -e "    The pipeline uses --cookies-from-browser chrome for YouTube downloads."
    echo -e "    Make sure you are logged into YouTube in Chrome and Chrome is closed"
    echo -e "    (or running with --lockfile-mode=none) when the pipeline runs."
    echo ""
    read -rp "  Continue anyway? [y/N]: " CONT
    [[ "$CONT" =~ ^[Yy]$ ]] || exit 1
fi

echo ""

# ─── Gather Configuration ─────────────────────────────────────────────────────

# If .env exists, offer to keep or replace
EXISTING_ENV=""
if [ -f "$ENV_FILE" ]; then
    echo -e "${WARN} Existing .env found."
    read -rp "  Reconfigure from scratch? (existing values shown as defaults) [y/N]: " RECONF
    if [[ "$RECONF" =~ ^[Yy]$ ]]; then
        EXISTING_ENV=$(cat "$ENV_FILE")
    else
        echo -e "  $PASS Keeping existing .env — skipping to verification."
        SKIP_CONFIG=1
    fi
fi

get_existing() {
    echo "$EXISTING_ENV" | grep "^${1}=" 2>/dev/null | cut -d'=' -f2- | sed 's/^"//;s/"$//'
}

if [ "${SKIP_CONFIG:-0}" -eq 0 ]; then
    echo ""
    echo -e "${BOLD}Configuration${RESET}"
    echo ""

    # ── Gemini API Key ──
    DEFAULT_KEY=$(get_existing "GEMINI_API_KEY")
    [ -n "$DEFAULT_KEY" ] && HINT=" [$DEFAULT_KEY]" || HINT=""
    while true; do
        read -rp "  Gemini API Key (for TTS):$HINT " GEMINI_API_KEY
        GEMINI_API_KEY="${GEMINI_API_KEY:-$DEFAULT_KEY}"
        if [[ "$GEMINI_API_KEY" =~ ^AIzaSy[A-Za-z0-9_-]{33}$ ]]; then
            echo -e "  $PASS Valid format"
            break
        else
            echo -e "  ${FAIL} Invalid format. Expected AIzaSy... (33 chars after prefix)"
            HINT=""
        fi
    done

    # ── Telegram Bot Token ──
    DEFAULT_TOKEN=$(get_existing "TELEGRAM_BOT_TOKEN")
    [ -n "$DEFAULT_TOKEN" ] && HINT=" [$DEFAULT_TOKEN]" || HINT=""
    while true; do
        read -rp "  Telegram Bot Token:$HINT " TELEGRAM_BOT_TOKEN
        TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$DEFAULT_TOKEN}"
        if [[ "$TELEGRAM_BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{35}$ ]]; then
            echo -e "  $PASS Valid format"
            break
        else
            echo -e "  ${FAIL} Invalid format. Expected 123456:ABCdef..."
            HINT=""
        fi
    done

    # ── Telegram Chat ID ──
    DEFAULT_CHAT=$(get_existing "TELEGRAM_CHAT_ID")
    [ -n "$DEFAULT_CHAT" ] && HINT=" [$DEFAULT_CHAT]" || HINT=""
    while true; do
        read -rp "  Telegram Chat ID:$HINT " TELEGRAM_CHAT_ID
        TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-$DEFAULT_CHAT}"
        if [[ "$TELEGRAM_CHAT_ID" =~ ^-?[0-9]+$ ]]; then
            echo -e "  $PASS Valid format"
            break
        else
            echo -e "  ${FAIL} Invalid format. Expected numeric ID (e.g., 8217367252)"
            HINT=""
        fi
    done

    # ── Playlist URL ──
    DEFAULT_PLAYLIST=$(get_existing "PLAYLIST_URL")
    [ -n "$DEFAULT_PLAYLIST" ] && HINT=" [$DEFAULT_PLAYLIST]" || HINT=""
    while true; do
        read -rp "  YouTube Playlist URL:$HINT " PLAYLIST_URL
        PLAYLIST_URL="${PLAYLIST_URL:-$DEFAULT_PLAYLIST}"
        if [[ "$PLAYLIST_URL" =~ ^https://www\.youtube\.com/playlist\?list= ]]; then
            echo -e "  $PASS Valid format"
            break
        else
            echo -e "  ${FAIL} Invalid format. Expected https://www.youtube.com/playlist?list=..."
            HINT=""
        fi
    done

    # ── TTS Voice (optional) ──
    DEFAULT_VOICE=$(get_existing "TTS_VOICE")
    DEFAULT_VOICE="${DEFAULT_VOICE:-Algenib}"
    read -rp "  TTS Voice [$DEFAULT_VOICE]: " TTS_VOICE
    TTS_VOICE="${TTS_VOICE:-$DEFAULT_VOICE}"

    # ── TTS Style (optional) ──
    DEFAULT_STYLE=$(get_existing "TTS_STYLE")
    read -rp "  TTS Style prefix (or Enter for none): " TTS_STYLE
    TTS_STYLE="${TTS_STYLE:-$DEFAULT_STYLE}"

    # ── Gemini Keys for script generation ──
    echo ""
    echo -e "${BOLD}Gemini keys for script generation${RESET}"
    echo "  (Used for Phase 3 script gen. Can be the same key as above."
    echo "   Add multiple keys for rotation to avoid rate limits.)"
    echo ""

    KEYS=()
    if [ -f "$KEYS_FILE" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] && KEYS+=("$line")
        done < "$KEYS_FILE"
    fi

    # Ensure the TTS key is in the list
    if ! printf '%s\n' "${KEYS[@]}" 2>/dev/null | grep -qxF "$GEMINI_API_KEY"; then
        KEYS=("$GEMINI_API_KEY" "${KEYS[@]}")
    fi

    echo "  Current keys: ${#KEYS[@]}"
    while true; do
        read -rp "  Add another key? (Enter to skip, or paste key): " EXTRA_KEY
        [ -z "$EXTRA_KEY" ] && break
        if [[ "$EXTRA_KEY" =~ ^AIzaSy[A-Za-z0-9_-]{33}$ ]]; then
            KEYS+=("$EXTRA_KEY")
            echo -e "  $PASS Added (${#KEYS[@]} total)"
        else
            echo -e "  ${FAIL} Invalid format, skipping"
        fi
    done

    # ── Write files ──
    echo ""
    echo -e "${BOLD}Writing configuration...${RESET}"

    # Backup existing
    [ -f "$ENV_FILE" ] && cp "$ENV_FILE" "${ENV_FILE}.bak"
    [ -f "$KEYS_FILE" ] && cp "$KEYS_FILE" "${KEYS_FILE}.bak"

    # Write .env
    {
        echo "GEMINI_API_KEY=$GEMINI_API_KEY"
        echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
        echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID"
        echo "PLAYLIST_URL=$PLAYLIST_URL"
        echo "TTS_VOICE=$TTS_VOICE"
        if [ -n "$TTS_STYLE" ]; then
            echo "TTS_STYLE=\"$TTS_STYLE\""
        fi
    } > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo -e "  $PASS $ENV_FILE"

    # Write gemini_keys.txt
    printf '%s\n' "${KEYS[@]}" > "$KEYS_FILE"
    chmod 600 "$KEYS_FILE"
    echo -e "  $PASS $KEYS_FILE (${#KEYS[@]} key(s))"

    echo ""
fi

# ─── Verification ─────────────────────────────────────────────────────────────

# Load the config
source "$ENV_FILE"

echo -e "${BOLD}Verifying connections...${RESET}"
ALL_OK=1

# Test Gemini API
echo -n "  Gemini API ... "
RESULT=$(curl -sf -X POST \
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=$GEMINI_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"contents":[{"parts":[{"text":"Say hello in one word"}]}],"generationConfig":{"maxOutputTokens":10}}' \
    2>/dev/null) && RC=0 || RC=1

if [ "$RC" -eq 0 ] && echo "$RESULT" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    echo -e "$PASS OK"
else
    echo -e "$FAIL Failed — check your GEMINI_API_KEY"
    ALL_OK=0
fi

# Test Telegram bot
echo -n "  Telegram bot ... "
BOT_INFO=$(curl -sf "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe" 2>/dev/null) && RC=0 || RC=1

if [ "$RC" -eq 0 ]; then
    BOT_NAME=$(echo "$BOT_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])" 2>/dev/null || echo "?")
    echo -e "$PASS @$BOT_NAME"
else
    echo -e "$FAIL Failed — check your TELEGRAM_BOT_TOKEN"
    ALL_OK=0
fi

# Test Telegram can send to chat
echo -n "  Telegram chat access ... "
SEND_TEST=$(curl -sf -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    -d text="🟢 Lambda Cut configured successfully!" \
    -d parse_mode="HTML" 2>/dev/null) && RC=0 || RC=1

if [ "$RC" -eq 0 ]; then
    echo -e "$PASS Message sent"
else
    echo -e "$FAIL Cannot send to chat $TELEGRAM_CHAT_ID — wrong chat ID or bot not added to chat"
    ALL_OK=0
fi

# Test playlist accessibility
echo -n "  YouTube playlist ... "
PL_CHECK=$(yt-dlp --flat-playlist --playlist-items 1 -j "$PLAYLIST_URL" 2>/dev/null) && RC=0 || RC=1

if [ "$RC" -eq 0 ]; then
    PL_TITLE=$(echo "$PL_CHECK" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title','?'))" 2>/dev/null || echo "?")
    echo -e "$PASS \"$PL_TITLE\""
else
    echo -e "$FAIL Cannot access playlist — check URL or cookies"
    ALL_OK=0
fi

# Test scripts are executable
for SCRIPT in lambda_cut.sh telegram_listener.sh generate_script.sh; do
    if [ ! -x "$WORKFLOW_DIR/$SCRIPT" ]; then
        chmod +x "$WORKFLOW_DIR/$SCRIPT"
        echo -e "  $WARN Made $SCRIPT executable"
    fi
done

echo ""

# ─── Summary ──────────────────────────────────────────────────────────────────

if [ "$ALL_OK" -eq 1 ]; then
    echo -e "${BOLD}========================================${RESET}"
    echo -e "${BOLD} All checks passed! You're ready to go.${RESET}"
    echo -e "${BOLD}========================================${RESET}"
    echo ""
    echo "  Run the pipeline:"
    echo "    ./workflows/lambda_cut.sh"
    echo ""
    echo "  Or start the Telegram listener:"
    echo "    ./workflows/telegram_listener.sh"
    echo ""
else
    echo -e "${BOLD}========================================${RESET}"
    echo -e "${BOLD} Some checks failed. Fix the issues above.${RESET}"
    echo -e "${BOLD}========================================${RESET}"
    echo ""
    echo "  Re-run this script after fixing:"
    echo "    ./workflows/onboard.sh"
    echo ""
fi
