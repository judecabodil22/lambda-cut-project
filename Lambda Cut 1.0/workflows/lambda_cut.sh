#!/bin/bash

# ==============================================================================
# Lambda Cut (VAAPI Optimized)
# ==============================================================================
set -e

# Prevent system sleep/suspend during pipeline execution
systemd-inhibit --what=sleep:idle --why="Running Lambda Cut" --who=$USER --mode=block &
INHIBIT_PID=$!
trap 'kill $INHIBIT_PID 2>/dev/null || true' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# Configuration
STREAMS_DIR="$WORKSPACE/streams"
TRANSCRIPTS_DIR="$WORKSPACE/transcripts"
SCRIPTS_DIR="$WORKSPACE/scripts"
TTS_DIR="$WORKSPACE/tts"
SHORTS_DIR="$WORKSPACE/shorts"
LOG_FILE="$WORKSPACE/pipeline.log"

PLAYLIST_URL=${PLAYLIST_URL:-}
TTS_DELAY=${TTS_DELAY:-300}
SCRIPT_DELAY=${SCRIPT_DELAY:-300}
TTS_VOICE=${TTS_VOICE:-Algenib}
TTS_STYLE=${TTS_STYLE:-}
STATUS_FILE="/tmp/pipeline_status"

# Flags
SKIP_DOWNLOAD=false
SKIP_TRANSCRIPTION=false
SKIP_SCRIPT_GEN=false
SKIP_SHORTS=false
SKIP_TTS=false
SELECTED_PHASES=""

# ----------------------------
# Helper Functions
# ----------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
log_error() { log "ERROR: $1"; }

set_status() { echo "$1" > "$STATUS_FILE"; }

retry() {
    local max_attempts=$1
    local delay=$2
    local description=$3
    shift 3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        log "   Attempt $attempt/$max_attempts: $description"
        if "$@"; then
            return 0
        fi
        if [ $attempt -lt $max_attempts ]; then
            log "   Failed, retrying in ${delay}s..."
            sleep $delay
            delay=$((delay * 2))
        fi
        attempt=$((attempt + 1))
    done
    return 1
}

notify_telegram() {
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$1" -d parse_mode="HTML" || log_error "Telegram failed"
}

progress_bar() {
    local current=$1
    local total=$2
    local width=30
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    local i
    printf "\r["
    for ((i=0; i<filled; i++)); do printf "#"; done
    for ((i=0; i<empty; i++)); do printf " "; done
    printf "] %d%%" $percent
}

# ----------------------------
# Parse Arguments
# ----------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                cat << EOF
Usage: $0 [OPTIONS]
Options:
  -phase N[,N,...]       Run only specified phase(s) (1-5). Overrides skip flags.
  -skip-phase-1          Skip Phase 1: Video Download
  -skip-phase-2          Skip Phase 2: Transcript Generation
  -skip-phase-3          Skip Phase 3: Script Generation
  -skip-phase-4          Skip Phase 4: Clip Generation
  -skip-phase-5          Skip Phase 5: TTS Generation
  -skip-all              Skip all phases (use with existing files)
  -h, --help             Show this help message
EOF
                exit 0
                ;;
            -phase)
                SELECTED_PHASES="$2"
                shift 2
                ;;
            -skip-phase-1) SKIP_DOWNLOAD=true; shift ;;
            -skip-phase-2) SKIP_TRANSCRIPTION=true; shift ;;
            -skip-phase-3) SKIP_SCRIPT_GEN=true; shift ;;
            -skip-phase-4) SKIP_SHORTS=true; shift ;;
            -skip-phase-5) SKIP_TTS=true; shift ;;
            -skip-all)
                SKIP_DOWNLOAD=true
                SKIP_TRANSCRIPTION=true
                SKIP_SCRIPT_GEN=true
                SKIP_SHORTS=true
                SKIP_TTS=true
                shift
                ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    # If specific phases selected, skip all phases then enable selected ones
    if [ -n "$SELECTED_PHASES" ]; then
        SKIP_DOWNLOAD=true
        SKIP_TRANSCRIPTION=true
        SKIP_SCRIPT_GEN=true
        SKIP_SHORTS=true
        SKIP_TTS=true

        IFS=',' read -ra PHASES <<< "$SELECTED_PHASES"
        for phase in "${PHASES[@]}"; do
            case $phase in
                1) SKIP_DOWNLOAD=false ;;
                2) SKIP_TRANSCRIPTION=false ;;
                3) SKIP_SCRIPT_GEN=false ;;
                4) SKIP_SHORTS=false ;;
                5) SKIP_TTS=false ;;
                *) echo "Invalid phase: $phase. Must be 1-5."; exit 1 ;;
            esac
        done
    fi
}

parse_args "$@"

# ----------------------------
# Create directories
# ----------------------------
mkdir -p "$STREAMS_DIR" "$TRANSCRIPTS_DIR" "$SCRIPTS_DIR" "$TTS_DIR" "$SHORTS_DIR"

# ----------------------------
# Phase 1: Download
# ----------------------------
if [ "$SKIP_DOWNLOAD" = false ]; then
    set_status "Phase 1: Downloading video..."
    log "🚀 Phase 1: Downloading 1440p stream..."
    notify_telegram "🚀 <b>Phase 1 Started</b>: Downloading video..."

    if ! retry 3 10 "Download video" yt-dlp --playlist-items 1 \
        --cookies-from-browser chrome \
        -f "bestvideo[height<=1440]+bestaudio/best[height<=1440]" \
        -o "$STREAMS_DIR/%(title)s.%(ext)s" "$PLAYLIST_URL" 2>&1 | tee -a "$LOG_FILE"; then
        log_error "Phase 1 failed after 3 attempts"
        notify_telegram "❌ <b>Phase 1 Failed</b>: Download failed after 3 attempts"
        set_status "Phase 1 FAILED"
        exit 1
    fi
    set_status "Phase 1 Complete"
    notify_telegram "✅ <b>Phase 1 Complete</b>: Video downloaded"
else
    log "🚀 Phase 1: Skipping download (SKIP_DOWNLOAD=true)"
    notify_telegram "✅ Phase 1 Skipped (using existing video)"
fi

LATEST_VIDEO=$(ls -t "$STREAMS_DIR"/*.{mkv,mp4,webm} 2>/dev/null | head -1)
[ -z "$LATEST_VIDEO" ] && { log_error "No video found"; exit 1; }

VIDEO_NAME=$(basename "$LATEST_VIDEO")
VIDEO_BASENAME=$(basename "$LATEST_VIDEO" .${LATEST_VIDEO##*.})
VIDEO_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$LATEST_VIDEO" | cut -d. -f1)
log "Target: $VIDEO_NAME ($VIDEO_DURATION sec)"

# ----------------------------
# Phase 2: Transcribe
# ----------------------------
if [ "$SKIP_TRANSCRIPTION" = false ]; then
    JSON_FILE="$TRANSCRIPTS_DIR/${VIDEO_BASENAME}.json"
    if [ ! -f "$JSON_FILE" ]; then
        set_status "Phase 2: Transcribing..."
        log "📝 Phase 2: Transcribing via stable-ts..."
        stable-ts -y "$LATEST_VIDEO" --output_dir "$TRANSCRIPTS_DIR" --output_format srt,json \
                  --word_timestamps False --vad True --language en 2>&1 | tee -a "$LOG_FILE"
        notify_telegram "✅ <b>Phase 2 Complete</b>: Transcript generated"
        set_status "Phase 2 Complete"
    else
        log "📝 Phase 2: Transcript already exists, skipping..."
        notify_telegram "✅ Phase 2 Skipped (transcript exists)"
    fi
else
    JSON_FILE=$(ls -t "$TRANSCRIPTS_DIR"/*.json 2>/dev/null | head -1)
    log "📄 Using existing transcript: $JSON_FILE"
fi

# ----------------------------
# Processing Loop (Hour by Hour)
# ----------------------------
NUM_HOURS=$((VIDEO_DURATION / 3600))
[ $NUM_HOURS -lt 1 ] && NUM_HOURS=1
log "📊 Video: $VIDEO_DURATION s = $NUM_HOURS hour(s)"

# ----------------------------
# Phase 3: Script Generation (one per hour)
# ----------------------------
if [ "$SKIP_SCRIPT_GEN" = false ]; then
    set_status "Phase 3: Generating scripts..."
    log "🎯 Phase 3: Generating scripts (one per hour)..."
    notify_telegram "🎯 <b>Phase 3 Started</b>: Generating $NUM_HOURS scripts..."
    for i in $(seq 1 $NUM_HOURS); do
        progress_bar $i $NUM_HOURS
        echo ""
        padded=$(printf "%03d" $i)
        HOUR_START=$(( (i-1)*3600 ))
        HOUR_END=$(( i*3600 ))
        [ $HOUR_END -gt $VIDEO_DURATION ] && HOUR_END=$VIDEO_DURATION

        # Checkpoint: skip if script already exists
        if [ -f "$SCRIPTS_DIR/script_$padded.txt" ]; then
            log "   Skipping script $i (exists)"
            continue
        fi

        log "   Processing hour $i: ${HOUR_START}s - ${HOUR_END}s"
        # Extract substantive transcript segments for the hour
        TEXT=$(python3 - "$JSON_FILE" $HOUR_START $HOUR_END <<'PYEOF'
import sys, json, re
file = sys.argv[1]
start = int(sys.argv[2])
end = int(sys.argv[3])
with open(file) as f:
    data = json.load(f)
collected = []
for seg in data["segments"]:
    if seg["start"] >= start and seg["end"] <= end:
        text = re.sub(r'<[^>]*>', '', seg["text"]).strip()
        if text and len(text.split()) >= 10:
            collected.append(text)
print("\n".join(collected))
PYEOF
        )
        if [ -z "$TEXT" ]; then
            log "   No substantive transcript for hour $i, skipping script"
            continue
        fi
        # Truncate to 3000 chars
        TEXT=$(echo "$TEXT" | head -c 3000)
        # Generate script via Gemini
        "$SCRIPT_DIR/generate_script.sh" "$i" "$TEXT" "$SCRIPTS_DIR/script_$padded.txt"
        word_count=$(wc -w < "$SCRIPTS_DIR/script_$padded.txt" 2>/dev/null || echo "0")
        log "   ✓ Script $i: $word_count words"
        set_status "Phase 3: Script $i/$NUM_HOURS generated"
        notify_telegram "📝 <b>Script $i/$NUM_HOURS generated</b> ($word_count words)"
        [ $i -lt $NUM_HOURS ] && { log "   ⏳ Waiting $SCRIPT_DELAY seconds"; sleep $SCRIPT_DELAY; }
    done
    log "   📝 Generated $NUM_HOURS scripts"
    set_status "Phase 3 Complete"
    notify_telegram "✅ <b>Phase 3 Complete</b>: $NUM_HOURS scripts generated"
else
    log "🎯 Phase 3: Skipping script generation (SKIP_SCRIPT_GEN=true)"
    notify_telegram "🎯 <b>Phase 3 Skipped</b> (SKIP_SCRIPT_GEN=true)"
fi

# ----------------------------
# Phase 4: Clip Generation (scene-based)
# ----------------------------
if [ "$SKIP_SHORTS" = false ]; then
    set -x
    set_status "Phase 4: Generating clips..."
    log "🎬 Phase 4: Generating clips (scene-based)..."
    notify_telegram "🎬 <b>Phase 4 Started</b>: Generating clips..."
    for i in $(seq 1 $NUM_HOURS); do
        HOUR_START=$(( (i-1)*3600 ))
        HOUR_END=$(( i*3600 ))
        [ $HOUR_END -gt $VIDEO_DURATION ] && HOUR_END=$VIDEO_DURATION
        padded_hour=$(printf "%03d" $i)

        # Find all scenes in this hour (write to temp file)
        SCENE_FILE=$(mktemp)
        python3 "$SCRIPT_DIR/smart_extract.py" "$JSON_FILE" $HOUR_START $HOUR_END > "$SCENE_FILE"
        if [ ! -s "$SCENE_FILE" ] || [ "$(cat "$SCENE_FILE")" = "NONE" ]; then
            log "   Hour $i: No scenes found"
            rm -f "$SCENE_FILE"
            continue
        fi

        clip_num=1
        while IFS='|' read -r CLIP_START CLIP_END TEXT; do
            [ -z "$CLIP_START" ] || ! [[ "$CLIP_START" =~ ^[0-9]+$ ]] && continue
            clip_name="short_${padded_hour}_${clip_num}.mp4"
            if [ -f "$SHORTS_DIR/$clip_name" ]; then
                log "   Skipping $clip_name (exists)"
                clip_num=$((clip_num + 1))
                continue
            fi

            DURATION=$(( CLIP_END - CLIP_START ))
            log "   Hour $i, scene $clip_num: ${CLIP_START}s - ${CLIP_END}s (${DURATION}s)"

            log "   Cutting clip: start=$CLIP_START, duration=$DURATION"
            # Determine encoder
            if [ -e "/dev/dri/renderD128" ]; then
                # VAAPI encoding (AMD GPU)
                if ffmpeg -y -vaapi_device /dev/dri/renderD128 -ss "$CLIP_START" -i "$LATEST_VIDEO" -t "$DURATION" \
                    -filter_complex "[0:a]loudnorm[aout]" \
                    -vf "format=nv12,hwupload" \
                    -c:v h264_vaapi -qp 18 \
                    -c:a aac -b:a 192k -map 0:v -map "[aout]" \
                    "$SHORTS_DIR/$clip_name" 2>&1; then
                    log "   ✓ $clip_name created (VAAPI)"
                else
                    log_error "Failed to create $clip_name with VAAPI"
                fi
            else
                # CPU fallback
                if ffmpeg -y -ss "$CLIP_START" -i "$LATEST_VIDEO" -t "$DURATION" \
                    -c:v libx264 -preset slow -crf 20 \
                    -profile:v high -level 4.2 -pix_fmt yuv420p \
                    -c:a aac -b:a 192k \
                    "$SHORTS_DIR/$clip_name" 2>&1; then
                    log "   ✓ $clip_name created (CPU)"
                else
                    log_error "Failed to create $clip_name with CPU"
                fi
            fi
            clip_num=$((clip_num + 1))
        done < "$SCENE_FILE"
        rm -f "$SCENE_FILE"
    done
    set +x
    log "   🎬 Clips generated"
    set_status "Phase 4 Complete"
    notify_telegram "✅ <b>Phase 4 Complete</b>: Clips generated"
else
    log "🎬 Phase 4: Skipping clip generation (SKIP_SHORTS=true)"
    notify_telegram "🎬 <b>Phase 4 Skipped</b> (SKIP_SHORTS=true)"
fi

# ----------------------------
# Phase 5: TTS Generation (one per hour)
# ----------------------------
if [ "$SKIP_TTS" = false ]; then
    set_status "Phase 5: Generating TTS..."
    log "🎙️ Phase 5: Generating TTS..."
    notify_telegram "🎙️ <b>Phase 5 Started</b>: Generating TTS..."
    for i in $(seq 1 $NUM_HOURS); do
        progress_bar $i $NUM_HOURS
        echo ""
        padded=$(printf "%03d" $i)
        # Generate WAV if not exists
        if [ ! -f "$TTS_DIR/tts_$padded.wav" ]; then
            if [ ! -f "$SCRIPTS_DIR/script_$padded.txt" ]; then
                log "   Script $i not found, skipping TTS"
                continue
            fi
            log "   Generating TTS for script $i..."
            python3 - "$SCRIPTS_DIR/script_$padded.txt" "$TTS_DIR/tts_$padded.pcm" "$GEMINI_API_KEY" "$TTS_VOICE" "$TTS_STYLE" <<'PYEOF'
import sys, json, urllib.request, base64
script, out, key, voice, style = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
with open(script) as f:
    text = f.read()
if style:
    text = f"{style} {text}"
data = {
    'contents': [{'parts': [{'text': text}]}],
    'generationConfig': {
        'responseModalities': ['AUDIO'],
        'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}
    }
}
req = urllib.request.Request(
    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={key}',
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode('utf-8'))
        audio = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
        import base64
        with open(out, 'wb') as f:
            f.write(base64.b64decode(audio))
except Exception as e:
    print(f"TTS error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
            if [ ! -f "$TTS_DIR/tts_$padded.pcm" ]; then
                log_error "   TTS failed for script $i"
                continue
            fi
            # Convert raw PCM (24kHz mono) to WAV (44.1kHz stereo)
            ffmpeg -y -f s16le -ar 24000 -ac 1 -i "$TTS_DIR/tts_$padded.pcm" -ar 44100 -ac 2 "$TTS_DIR/tts_$padded.wav" 2>&1 | tee -a "$LOG_FILE"
            rm -f "$TTS_DIR/tts_$padded.pcm"
            log "   ✓ tts_$padded.wav created"
            set_status "Phase 5: TTS $i/$NUM_HOURS generated"
            notify_telegram "🎙️ <b>TTS $i/$NUM_HOURS generated</b>"
        else
            log "   TTS $i WAV exists, skipping generation"
        fi

        # Generate SRT from TTS WAV
        if [ ! -f "$TTS_DIR/tts_$padded.srt" ]; then
            log "   Generating SRT for tts_$padded.wav..."
            stable-ts "$TTS_DIR/tts_$padded.wav" --device cpu --word_timestamps False --language en \
                -o "$TTS_DIR/tts_$padded.srt" 2>&1 | tee -a "$LOG_FILE"
            [ -f "$TTS_DIR/tts_$padded.srt" ] && log "   ✓ tts_$padded.srt created" || log_error "   SRT generation failed for tts_$padded"
        else
            log "   tts_$padded.srt exists, skipping SRT generation"
        fi
        [ $i -lt $NUM_HOURS ] && { log "   ⏳ Waiting $TTS_DELAY seconds"; sleep $TTS_DELAY; }
    done
    log "   🎙️ TTS generation done"
    set_status "Phase 5 Complete"
    notify_telegram "✅ <b>Phase 5 Complete</b>: TTS generation done"
else
    log "🎙️ Phase 5: Skipping TTS generation (SKIP_TTS=true)"
    notify_telegram "🎙️ <b>Phase 5 Skipped</b> (SKIP_TTS=true)"
fi

log "✅ Pipeline Complete!"
set_status "Pipeline Complete"

# Send summary with file counts
scripts_count=$(ls "$SCRIPTS_DIR"/*.txt 2>/dev/null | wc -l)
clips_count=$(ls "$SHORTS_DIR"/*.mp4 2>/dev/null | wc -l)
tts_wav_count=$(ls "$TTS_DIR"/*.wav 2>/dev/null | wc -l)
tts_srt_count=$(ls "$TTS_DIR"/*.srt 2>/dev/null | wc -l)
transcript_count=$(ls "$TRANSCRIPTS_DIR"/*.json 2>/dev/null | wc -l)

notify_telegram "✅ <b>Pipeline Complete!</b>

<b>Video:</b> $VIDEO_NAME
<b>Duration:</b> $((VIDEO_DURATION / 3600))h $((VIDEO_DURATION % 3600 / 60))m

📊 <b>Created Files:</b>
📝 Scripts: $scripts_count
🎬 Clips: $clips_count
🎙️ TTS WAVs: $tts_wav_count
📄 TTS SRTs: $tts_srt_count
📋 Transcripts: $transcript_count

<b>Total output files:</b> $((scripts_count + clips_count + tts_wav_count + tts_srt_count))"