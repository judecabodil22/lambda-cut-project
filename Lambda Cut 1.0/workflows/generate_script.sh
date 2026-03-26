#!/bin/bash
# generate_script.sh - Generate a script using Gemini with key rotation and retry
# Usage: generate_script.sh <script_number> <transcript_text> <output_file>

set -e

SCRIPT_NUM="$1"
TEXT="$2"
OUTPUT_FILE="$3"
KEYS_FILE="${4:-$(dirname "$0")/gemini_keys.txt}"

if [ -z "$SCRIPT_NUM" ] || [ -z "$TEXT" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <script_number> <transcript_text> <output_file> [keys_file]"
    exit 1
fi

# Write transcript to temporary file
TMP_TRANSCRIPT=$(mktemp)
echo "$TEXT" > "$TMP_TRANSCRIPT"

# Call Python script
python3 - "$TMP_TRANSCRIPT" "$OUTPUT_FILE" "$SCRIPT_NUM" "$KEYS_FILE" <<'PYEOF'
import sys, json, urllib.request, urllib.error, time, os

transcript_file = sys.argv[1]
output_file = sys.argv[2]
script_num = int(sys.argv[3])
keys_file = sys.argv[4]

with open(transcript_file, 'r') as f:
    transcript = f.read()

if not os.path.exists(keys_file):
    print(f"Keys file not found: {keys_file}", file=sys.stderr)
    sys.exit(1)

with open(keys_file) as f:
    keys = [line.strip() for line in f if line.strip()]

if not keys:
    print("No API keys found", file=sys.stderr)
    sys.exit(1)

# ----------------------------
# 1. Limit transcript size
# ----------------------------
MAX_CHARS = 3000
if len(transcript) > MAX_CHARS:
    transcript = transcript[:MAX_CHARS]

# ----------------------------
# 2. Rate limiter (global)
# ----------------------------
LAST_CALL_FILE = "/tmp/gemini_last_call.txt"

def rate_limit(min_interval=6):
    now = time.time()
    try:
        with open(LAST_CALL_FILE, "r") as f:
            last = float(f.read().strip())
    except:
        last = 0
    wait = min_interval - (now - last)
    if wait > 0:
        time.sleep(wait)
    with open(LAST_CALL_FILE, "w") as f:
        f.write(str(time.time()))

# ----------------------------
# 3. Smart key rotation
# ----------------------------
start_idx = (script_num - 1) % len(keys)

prompt = f"""Generate a script for YouTube Shorts narrating the events from the protagonist's POV, blending first-person narration with direct quotes from the transcript. Format the script as follows:

Title: "Script {script_num}: [Create a fitting title]"

The title must use the exact script number provided ({script_num}). Script body should be continuous prose, not bullet points. Include 2-3 direct quotes from the transcript in italics. The narration should be in first person. End with a cliffhanger.

Example:
Title: Script 2: The Widow's Enterprise

I’m standing before the spirit of Lucy, a woman who hasn't realized her tavern days are long over. She talks about the life she left behind in England with her husband as if she’s still waiting for the next customer to walk through the door.
My husband and I ran a tavern in England.

She treats her death like a business transaction that went wrong. Even as a ghost, she’s cold and calculating, demanding payment in blood because she never gave anything away for free while she was alive.
I am a woman of enterprise and no one drinks for free.

She’s convinced the baker killed her because he couldn't get what he wanted. In her mind, her death is just another debt he hasn't settled yet.
Meen, for he would not pay me for my work.

It’s my task to weigh her words against the truth and see if the baker truly poisoned her or if her spirit is just feeding on its own bitterness.
Are you sure he poisoned you?

IMPORTANT: The script must be under 150 words.

Now generate a script based ONLY on this scene dialogue:
{transcript}"""

data = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.7,
        "maxOutputTokens": 512
    }
}

script = None

for i in range(len(keys)):
    api_key = keys[(start_idx + i) % len(keys)]
    print(f"Trying API key: ...{api_key[-6:]}", file=sys.stderr)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    for attempt in range(3):
        try:
            rate_limit()
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                script = result['candidates'][0]['content']['parts'][0]['text']
                print(f"Success with key ...{api_key[-6:]}", file=sys.stderr)
                break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (2 ** attempt) * 15  # 15s, 30s, 60s
                print(f"Rate limited, waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"HTTP Error with key ...{api_key[-6:]}: {e}", file=sys.stderr)
                break
        except Exception as e:
            print(f"Error with key ...{api_key[-6:]}: {e}", file=sys.stderr)
            break
    if script is not None:
        break
    else:
        print(f"Key ...{api_key[-6:]} failed, trying next...", file=sys.stderr)

if script is None:
    print("All keys failed, using raw transcript", file=sys.stderr)
    script = transcript  # fallback

with open(output_file, 'w') as f:
    f.write(script)
PYEOF

# Clean up
rm -f "$TMP_TRANSCRIPT"