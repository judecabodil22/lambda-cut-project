#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env"

WORKSPACE="$SCRIPT_DIR"
LAST_UPDATE_FILE="/tmp/telegram_last_update"
ENV_FILE="$SCRIPT_DIR/.env"

get_updates() {
    local offset=""
    if [ -f "$LAST_UPDATE_FILE" ]; then
        offset="&offset=$(cat "$LAST_UPDATE_FILE")"
    fi

    curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates?limit=3&timeout=30$offset"
}

send_message() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$message" \
        -d parse_mode="HTML"
}

update_env_var() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
    else
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
}

get_env_var() {
    local key="$1"
    local default="${2:-}"
    grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed 's/^"//;s/"$//' || echo "$default"
}

run_pipeline_with_flags() {
    local flags="$1"
    if pgrep -f "lambda_cut.sh" > /dev/null 2>&1; then
        send_message "⚙️ Pipeline is already running..."
        return
    fi
    send_message "🔄 <b>Pipeline triggered!</b> Flags: $flags"
    cd "$WORKSPACE"
    # shellcheck disable=SC2086
    nohup bash -c "source .env && ./lambda_cut.sh $flags" >> "$WORKSPACE/pipeline.log" 2>&1 &
    send_message "✅ <b>Pipeline started in background!</b> Check /status for updates."
}

process_command() {
    local full_msg="$1"
    local chat_id="$2"
    local message_id="$3"

    local cmd="${full_msg%% *}"
    local args="${full_msg#* }"
    [ "$args" = "$cmd" ] && args=""

    case "$cmd" in
        /run_pipeline|/runpipeline)
            run_pipeline_with_flags ""
            ;;
        /run_phase|/runphase)
            if [ -z "$args" ]; then
                send_message "Usage: /run_phase 5 or /run_phase 2,3\nPhases: 1 Download  2 Transcribe  3 Scripts  4 Clips  5 TTS"
            else
                run_pipeline_with_flags "-phase $args"
            fi
            ;;
        /skip_phase|/skipphase)
            if [ -z "$args" ]; then
                send_message "Usage: /skip_phase 1 or /skip_phase 1,2\nPhases: 1 Download  2 Transcribe  3 Scripts  4 Clips  5 TTS"
            else
                local flags=""
                IFS=',' read -ra PHASES <<< "$args"
                for p in "${PHASES[@]}"; do
                    flags="$flags -skip-phase-$p"
                done
                run_pipeline_with_flags "$flags"
            fi
            ;;
        /set_voice|/setvoice)
            if [ -z "$args" ]; then
                send_message "❓ Usage: /set_voice Algenib\nVoices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat, Achernar, Alnilam, Laomedeia"
            else
                update_env_var "TTS_VOICE" "$args"
                send_message "🎙️ <b>Voice set to:</b> $args"
            fi
            ;;
        /set_style|/setstyle)
            if [ -z "$args" ]; then
                # Clear style
                update_env_var "TTS_STYLE" ""
                send_message "🎨 <b>Style cleared.</b> TTS will use default voice delivery."
            else
                update_env_var "TTS_STYLE" "$args"
                send_message "🎨 <b>Style set to:</b> $args"
            fi
            ;;
        /config|/settings)
            local voice=$(get_env_var "TTS_VOICE" "Algenib")
            local style=$(get_env_var "TTS_STYLE" "(none)")
            [ -z "$style" ] && style="(none)"
            local status="💤 Idle"
            pgrep -f "lambda_cut.sh" > /dev/null 2>&1 && status="⚙️ Running"

            local wav_count=$(ls "$WORKSPACE/../tts/"*.wav 2>/dev/null | wc -l)
            local srt_count=$(ls "$WORKSPACE/../tts/"*.srt 2>/dev/null | wc -l)
            local script_count=$(ls "$WORKSPACE/../scripts/"*.txt 2>/dev/null | wc -l)
            local clip_count=$(ls "$WORKSPACE/../shorts/"*.mp4 2>/dev/null | wc -l)

            send_message "⚙️ <b>Current Config:</b>
🎙️ Voice: $voice
🎨 Style: $style
📊 Status: $status

📁 <b>Files:</b>
Scripts: $script_count
Clips: $clip_count
TTS WAVs: $wav_count
TTS SRTs: $srt_count"
            ;;
        /status)
            if pgrep -f "lambda_cut.sh" > /dev/null 2>&1; then
                local pipeline_status="Running (no details)"
                if [ -f "/tmp/pipeline_status" ]; then
                    pipeline_status=$(cat /tmp/pipeline_status)
                fi
                send_message "⚙️ Pipeline is running: $pipeline_status"
            else
                local last_status="Idle"
                if [ -f "/tmp/pipeline_status" ]; then
                    last_status=$(cat /tmp/pipeline_status)
                fi
                send_message "💤 Pipeline is idle. Last status: $last_status"
            fi
            ;;
        /logs)
            if [ -f "$WORKSPACE/pipeline.log" ]; then
                local last_lines=$(tail -20 "$WORKSPACE/pipeline.log" | python3 -c "import sys; import html; print(html.escape(sys.stdin.read()))" | head -1500)
                send_message "📜 Last 20 lines:
$last_lines"
            else
                send_message "📭 No pipeline logs found."
            fi
            ;;
        /help)
            send_message "<b>Available Commands</b>

/run_pipeline - Run full pipeline
/run_phase 5 - Run phase 5 only
/run_phase 2,3 - Run phases 2 and 3
/skip_phase 1,2 - Skip phases 1 and 2

<b>Phases</b>  1 Download  2 Transcribe  3 Scripts  4 Clips  5 TTS

/set_voice Puck - Change TTS voice
/set_style Say in a Scottish accent - Set style prefix
/set_style - Clear style

/config - Show settings and file counts
/status - Pipeline running or idle
/logs - Last 20 log lines
/help - This message"
            ;;
        *)
            send_message "❓ Unknown command. Use /help for available commands."
            ;;
    esac
}

echo "🤖 Sophia Telegram Listener started..."
echo "Waiting for commands..."

while true; do
    RESPONSE=$(get_updates)

    if echo "$RESPONSE" | grep -q '"ok":true'; then
        UPDATE_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['update_id'])" 2>/dev/null)
        MSG_TEXT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['message']['text'])" 2>/dev/null)
        MSG_CHAT_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['message']['chat']['id'])" 2>/dev/null)
        MSG_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['message']['message_id'])" 2>/dev/null)

        if [ -n "$UPDATE_ID" ] && [ "$MSG_CHAT_ID" = "$TELEGRAM_CHAT_ID" ]; then
            echo "$((UPDATE_ID + 1))" > "$LAST_UPDATE_FILE"

            if [ -n "$MSG_TEXT" ]; then
                echo "📩 Received: $MSG_TEXT"
                process_command "$MSG_TEXT" "$MSG_CHAT_ID" "$MSG_ID"
            fi
        fi
    fi

    sleep 5
done
