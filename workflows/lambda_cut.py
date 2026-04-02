#!/usr/bin/env python3
"""
Lambda Cut — YouTube Shorts Pipeline
Combines: lambda_cut.sh, telegram_listener.sh, generate_script.sh, onboard.sh
"""
import argparse, base64, glob, json, os, random, re, shutil, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request
from update_manager import (
    get_local_version,
    get_release_notes,
    check_for_updates,
    perform_update,
    cleanup_old_backups,
)
from keychain_manager import (
    get_gemini_keys,
    get_service_password,
    set_gemini_keys,
    set_service_password,
)
# ─── Paths ────────────────────────────────────────────────────────────────────
DEFAULT_WORKSPACE = os.path.expanduser("~/lambda_cut")

def _find_workspace():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("WORKSPACE="):
                    return line.strip().split("=", 1)[1].strip().strip('"')
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKSPACE    = _find_workspace()
WORKFLOW_DIR = os.path.join(WORKSPACE, "workflows")
ENV_FILE     = os.path.join(WORKSPACE, ".env")
KEYS_FILE    = os.path.join(WORKSPACE, "gemini_keys.txt")
LOG_FILE     = os.path.join(WORKSPACE, "pipeline.log")
STATUS_FILE  = "/tmp/pipeline_status"
LAST_CALL    = "/tmp/gemini_last_call.txt"

STREAMS_DIR      = os.path.join(WORKSPACE, "streams")
TRANSCRIPTS_DIR  = os.path.join(WORKSPACE, "transcripts")
SCRIPTS_DIR      = os.path.join(WORKSPACE, "scripts")
TTS_DIR          = os.path.join(WORKSPACE, "tts")
SHORTS_DIR       = os.path.join(WORKSPACE, "shorts")
OUTPUT_DIR       = os.path.join(WORKSPACE, "output")

STREAMING = False  # set True when called from listener
PIPELINE_RUNNING = False
LISTENER_RESTART = False  # set True when update requires restart
PIPELINE_STOP_REQUESTED = False  # set True to request pipeline stop
LISTENER_RUNNING = True  # set False to stop listener
PID_FILE = "/tmp/lambda_cut_listener.pid"
OFFSET_FILE = "/tmp/lambda_cut_listener_offset"

# Round-robin state for script generation (initialized per pipeline run)
_rr_variants = []
_rr_perspectives = []
_rr_voices = []
_rr_styles = []
_rr_script_index = 0
_rr_tts_index = 0

def _init_round_robin(num_scripts):
    """Initialize round-robin lists - shuffled once per pipeline run."""
    global _rr_variants, _rr_perspectives, _rr_voices, _rr_styles, _rr_script_index, _rr_tts_index
    import random
    
    # Get all options
    all_variants = list(SCRIPT_VARIANTS.keys())
    all_perspectives = list(SCRIPT_PERSPECTIVES)
    all_voices = [
        "Vindemiatrix", "Aoede", "Callirrhoe", "Gacrux", "Sulafat", "Leda",
        "Kore", "Enceladus", "Erinome", "Despina", "Alnilam", "Laomedeia",
        "Achernar", "Pulcherrima", "Zephyr", "Puck", "Charon", "Fenrir",
        "Orus", "Iapetus", "Umbriel", "Algieba", "Rasalgethi", "Schedar",
        "Sadachbia", "Sadaltager", "Achird", "Zubenelgenubi", "Algenib", "Autonoe"
    ]
    all_styles = list(TTS_STYLE_OPTIONS)
    
    # Shuffle once at start
    random.shuffle(all_variants)
    random.shuffle(all_perspectives)
    random.shuffle(all_voices)
    random.shuffle(all_styles)
    
    # Extend to cover all scripts (cycle through if more scripts than options)
    _rr_variants = (all_variants * ((num_scripts // len(all_variants)) + 2))[:num_scripts]
    _rr_perspectives = (all_perspectives * ((num_scripts // len(all_perspectives)) + 2))[:num_scripts]
    _rr_voices = (all_voices * ((num_scripts // len(all_voices)) + 2))[:num_scripts]
    _rr_styles = (all_styles * ((num_scripts // len(all_styles)) + 2))[:num_scripts]
    _rr_script_index = 0
    _rr_tts_index = 0
    
    print(f"Round-robin initialized: {len(_rr_variants)} variants, {len(_rr_perspectives)} perspectives")

def _get_next_round_robin():
    """Get next round-robin item and advance index."""
    global _rr_script_index
    if not _rr_variants:
        return random.choice(list(SCRIPT_VARIANTS.keys())), random.choice(SCRIPT_PERSPECTIVES)
    
    variant = _rr_variants[_rr_script_index] if _rr_script_index < len(_rr_variants) else random.choice(list(SCRIPT_VARIANTS.keys()))
    perspective = _rr_perspectives[_rr_script_index] if _rr_script_index < len(_rr_perspectives) else random.choice(SCRIPT_PERSPECTIVES)
    _rr_script_index += 1
    return variant, perspective

def _get_next_voice_style():
    """Get next round-robin voice and style (separate from script round-robin)."""
    global _rr_tts_index
    if not _rr_voices:
        all_voices = [
            "Vindemiatrix", "Aoede", "Callirrhoe", "Gacrux", "Sulafat", "Leda",
            "Kore", "Enceladus", "Erinome", "Despina", "Alnilam", "Laomedeia",
            "Achernar", "Pulcherrima", "Zephyr", "Puck", "Charon", "Fenrir",
            "Orus", "Iapetus", "Umbriel", "Algieba", "Rasalgethi", "Schedar",
            "Sadachbia", "Sadaltager", "Achird", "Zubenelgenubi", "Algenib", "Autonoe"
        ]
        return random.choice(all_voices), random.choice(TTS_STYLE_OPTIONS)
    
    voice = _rr_voices[_rr_tts_index] if _rr_tts_index < len(_rr_voices) else random.choice(_rr_voices)
    style = _rr_styles[_rr_tts_index] if _rr_tts_index < len(_rr_styles) else random.choice(_rr_styles)
    _rr_tts_index += 1
    return voice, style

# ─── Environment ──────────────────────────────────────────────────────────────
def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k] = v.strip('"').strip("'")
    return env

ENV = load_env()

def env(key, default=""):
    keychain_map = {
        "GEMINI_API_KEY": "gemini-api-key",
        "TELEGRAM_BOT_TOKEN": "telegram-bot-token",
        "TELEGRAM_CHAT_ID": "telegram-chat-id",
    }
    if key in keychain_map:
        keychain_key = keychain_map[key]
        keychain_value = get_service_password(keychain_key)
        if keychain_value:
            return keychain_value
    return ENV.get(key, default)

# ─── Logging ──────────────────────────────────────────────────────────────────
def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass

def log_error(msg):
    log(f"ERROR: {msg}")

def set_status(msg):
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(msg)
    except OSError:
        pass

# ─── Telegram ─────────────────────────────────────────────────────────────────
def tg_send(msg, parse_mode=None):
    token = env("TELEGRAM_BOT_TOKEN")
    chat  = env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        params = {"chat_id": chat, "text": msg}
        if parse_mode:
            params["parse_mode"] = parse_mode
        data = urllib.parse.urlencode(params).encode()
        req  = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                      data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        print(f"Telegram send error: {e}")

def tg_send_menu(msg, reply_markup=None):
    token = env("TELEGRAM_BOT_TOKEN")
    chat  = env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        params = {"chat_id": chat, "text": msg}
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        data = urllib.parse.urlencode(params).encode()
        req  = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                      data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Menu send error: {e}")

def tg_answer_callback(callback_id, text=None):
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    try:
        params = {"callback_query_id": callback_id}
        if text:
            params["text"] = text
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                                    data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Callback answer error: {e}")
        if isinstance(e, urllib.error.HTTPError):
            try:
                body = e.read().decode()
            except:
                body = "No response body"
            log_error(f"Telegram callback: {e.code} {e.reason} - {body[:200]}")

def notify(msg):
    if STREAMING:
        tg_send(msg)

# ─── Inline Menu Functions ───────────────────────────────────────────────────
def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "📊 Status", "callback_data": "menu_status"}, {"text": "▶️ Run Pipeline", "callback_data": "menu_pipeline"}],
            [{"text": "📝 Scripts", "callback_data": "menu_scripts"}, {"text": "🎬 Clips", "callback_data": "menu_clips"}],
            [{"text": "🎤 TTS", "callback_data": "menu_tts"}, {"text": "🔄 Restart", "callback_data": "menu_restart"}],
            [{"text": "⚙️ Config", "callback_data": "menu_config"}, {"text": "📋 Help", "callback_data": "menu_help"}],
            [{"text": "🔍 Update", "callback_data": "menu_update"}, {"text": "🛑 Stop", "callback_data": "menu_stop"}]
        ]
    }

def get_run_menu():
    return {
        "inline_keyboard": [
            [{"text": "📥 Full Pipeline", "callback_data": "run_full"}, {"text": "📥 Download", "callback_data": "run_phase1"}],
            [{"text": "📝 Scripts", "callback_data": "run_phase3"}, {"text": "🎬 Clips", "callback_data": "run_phase4"}],
            [{"text": "🎤 TTS", "callback_data": "run_phase5"}, {"text": "⬅️ Back", "callback_data": "menu_back"}]
        ]
    }

def get_config_menu():
    return {
        "inline_keyboard": [
            [{"text": "🎤 Voice", "callback_data": "config_voice"}, {"text": "📝 Index", "callback_data": "config_index"}],
            [{"text": "🎵 Style", "callback_data": "config_style"}, {"text": "🎮 Game", "callback_data": "config_game"}],
            [{"text": "📁 Source", "callback_data": "config_source"}, {"text": "📂 Files", "callback_data": "files_browse"}],
            [{"text": "⬅️ Back", "callback_data": "menu_back"}]
        ]
    }

def get_help_menu():
    return {
        "inline_keyboard": [
            [{"text": "📖 Commands", "callback_data": "help_commands"}, {"text": "💬 Phases", "callback_data": "help_phases"}],
            [{"text": "🎤 Voices", "callback_data": "help_voices"}, {"text": "⬅️ Back", "callback_data": "menu_back"}]
        ]
    }

def get_voice_menu():
    voices = ["Vindemiatrix", "Aoede", "Callirrhoe", "Gacrux", "Sulafat", "Leda",
              "Kore", "Enceladus", "Erinome", "Despina", "Alnilam", "Laomedeia",
              "Achernar", "Pulcherrima", "Zephyr", "Puck", "Charon", "Fenrir",
              "Orus", "Iapetus", "Umbriel", "Algieba", "Rasalgethi", "Schedar",
              "Sadachbia", "Sadaltager", "Achird", "Zubenelgenubi", "Algenib", "Autonoe"]
    current = env("TTS_VOICE", "")
    keyboard = []
    for i in range(0, len(voices), 3):
        row = []
        for v in voices[i:i+3]:
            mark = "✓" if v == current else ""
            row.append({"text": f"{v} {mark}".strip(), "callback_data": f"set_voice_{v}"})
        keyboard.append(row)
    keyboard.append([{"text": "⬅️ Back", "callback_data": "menu_config"}])
    return {"inline_keyboard": keyboard}

def get_index_menu():
    keyboard = [
        [{"text": "1", "callback_data": "set_index_1"}, {"text": "2", "callback_data": "set_index_2"}, {"text": "3", "callback_data": "set_index_3"}, {"text": "4", "callback_data": "set_index_4"}, {"text": "5", "callback_data": "set_index_5"}],
        [{"text": "6", "callback_data": "set_index_6"}, {"text": "7", "callback_data": "set_index_7"}, {"text": "8", "callback_data": "set_index_8"}, {"text": "9", "callback_data": "set_index_9"}, {"text": "10", "callback_data": "set_index_10"}],
        [{"text": "⬅️ Back", "callback_data": "menu_config"}]
    ]
    return {"inline_keyboard": keyboard}

def get_style_menu():
    styles = ["Default", "Narrative", "Exciting", "Mysterious", "Funny", "Emotional", "Action", "Horror", "Romance", "Documentary"]
    current = env("TTS_STYLE", "")
    keyboard = []
    for i in range(0, len(styles), 2):
        row = []
        for s in styles[i:i+2]:
            mark = "✓" if s == current else ""
            row.append({"text": f"{s} {mark}".strip(), "callback_data": f"set_style_{s}"})
        keyboard.append(row)
    keyboard.append([{"text": "⬅️ Back", "callback_data": "menu_config"}])
    return {"inline_keyboard": keyboard}

def get_game_menu():
    games = ["Life is Strange", "Before the Storm", "True Colors", "Double Exposure", "Spider-Man", "God of War", "Hogwarts Legacy", "The Last of Us"]
    current = env("GAME_TITLE", "")
    keyboard = []
    for i in range(0, len(games), 2):
        row = []
        for g in games[i:i+2]:
            mark = "✓" if g == current else ""
            row.append({"text": f"{g} {mark}".strip(), "callback_data": f"set_game_{g}"})
        keyboard.append(row)
    keyboard.append([{"text": "🗑️ Clear", "callback_data": "set_game__clear"}])
    keyboard.append([{"text": "⬅️ Back", "callback_data": "menu_config"}])
    return {"inline_keyboard": keyboard}

def get_files_menu():
    sc = count_files(os.path.join(SCRIPTS_DIR, "*.txt"))
    cc = count_files(os.path.join(SHORTS_DIR, "*.mp4"))
    wc = count_files(os.path.join(TTS_DIR, "*.wav"))
    return {
        "inline_keyboard": [
            [{"text": f"📝 Scripts ({sc})", "callback_data": "files_scripts"}, {"text": f"🎬 Clips ({cc})", "callback_data": "files_clips"}],
            [{"text": f"🎤 TTS ({wc})", "callback_data": "files_tts"}],
            [{"text": "🧹 Cleanup All", "callback_data": "cleanup_files"}, {"text": "⬅️ Back", "callback_data": "menu_config"}]
        ]
    }

def handle_menu_callback(callback_data):
    """Handle menu button callbacks."""
    if callback_data == "menu_status":
        return _get_rich_status()
    elif callback_data == "menu_pipeline":
        return None, get_run_menu()
    elif callback_data == "menu_scripts":
        return "📝 Running Phase 3...", "run_phase 3"
    elif callback_data == "menu_clips":
        return "🎬 Running Phase 4...", "run_phase 4"
    elif callback_data == "menu_tts":
        return "🎤 Running Phase 5...", "run_phase 5"
    elif callback_data == "menu_restart":
        return "🔄 Restarting listener...", "restart_listener"
    elif callback_data == "menu_config":
        return None, get_config_menu()
    elif callback_data == "menu_help":
        return None, get_help_menu()
    elif callback_data == "menu_update":
        script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        update_info = check_for_updates(script_root)
        if update_info.get("update_available"):
            remote_ver = update_info.get("remote_version", "Unknown")
            return f"🔔 Update available: v{remote_ver}\nRun /update to install.", "run_update"
        return "✅ You have the latest version."
    elif callback_data == "menu_stop":
        return "🛑 Stopping pipeline...", "stop_pipeline"
    elif callback_data == "menu_back":
        return None, get_main_menu()
    elif callback_data == "run_full":
        return "▶️ Running full pipeline...", "run_pipeline"
    elif callback_data == "run_phase1":
        return "📥 Running Phase 1...", "run_phase 1"
    elif callback_data == "run_phase3":
        return "📝 Running Phase 3...", "run_phase 3"
    elif callback_data == "run_phase4":
        return "🎬 Running Phase 4...", "run_phase 4"
    elif callback_data == "run_phase5":
        return "🎤 Running Phase 5...", "run_phase 5"
    elif callback_data == "config_voice":
        return None, get_voice_menu()
    elif callback_data == "config_index":
        return None, get_index_menu()
    elif callback_data == "config_style":
        return None, get_style_menu()
    elif callback_data == "config_game":
        return None, get_game_menu()
    elif callback_data == "config_source":
        return "📁 Recording path: " + env("RECORDING_PATH", "~/Videos/Recordings")
    elif callback_data == "files_browse":
        return None, get_files_menu()
    elif callback_data == "files_scripts":
        return _get_files_list("scripts")
    elif callback_data == "files_clips":
        return _get_files_list("clips")
    elif callback_data == "files_tts":
        return _get_files_list("tts")
    elif callback_data == "files_shorts":
        return _get_files_list("shorts")
    elif callback_data == "quick_stop":
        return "🛑 Stopping pipeline...", "stop_pipeline"
    elif callback_data == "quick_restart":
        return "🔄 Restarting listener...", "restart_listener"
    elif callback_data == "quick_status":
        return _get_rich_status()
    elif callback_data == "quick_clean":
        return "🧹 Cleaning up files...", "cleanup_files"
    elif callback_data == "run_update":
        return "🔄 Updating Lambda Cut...", "do_update"
    elif callback_data == "set_voice_":
        return None, get_voice_menu()
    elif callback_data.startswith("set_voice_"):
        voice = callback_data.replace("set_voice_", "")
        update_env_var("TTS_VOICE", voice)
        return f"✅ Voice set to: {voice}"
    elif callback_data.startswith("set_index_"):
        index = callback_data.replace("set_index_", "")
        update_env_var("PLAYLIST_INDEX", index)
        return f"✅ Playlist index set to: {index}"
    elif callback_data.startswith("set_style_"):
        style = callback_data.replace("set_style_", "")
        update_env_var("TTS_STYLE", style)
        return f"✅ Style set to: {style}"
    elif callback_data.startswith("set_game_"):
        game = callback_data.replace("set_game_", "")
        if game == "_clear":
            update_env_var("GAME_TITLE", "")
            return "✅ Game title cleared"
        update_env_var("GAME_TITLE", game)
        return f"✅ Game set to: {game}"
    elif callback_data == "cleanup_files":
        count = cleanup_all_files()
        return f"🧹 Cleaned up {count} file(s)"
    elif callback_data == "do_update":
        return _do_update_menu()
    else:
        return "Unknown action"


def _get_rich_status():
    """Get rich status card with file counts and pipeline info."""
    script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_ver = get_local_version(script_root)
    
    # File counts
    sc = count_files(os.path.join(SCRIPTS_DIR, "*.txt"))
    cc = count_files(os.path.join(SHORTS_DIR, "*.mp4"))
    wc = count_files(os.path.join(TTS_DIR, "*.wav"))
    tc = count_files(os.path.join(TRANSCRIPTS_DIR, "*.json"))
    
    # Pipeline status
    s = open(STATUS_FILE).read() if os.path.exists(STATUS_FILE) else ""
    if PIPELINE_RUNNING:
        status_line = f"🔄 Running: {s}"
    elif s:
        status_line = f"💤 Idle — Last: {s}"
    else:
        status_line = "💤 Idle"
    
    # Voice and style
    voice = env("TTS_VOICE", "Not set")
    style = env("TTS_STYLE", "Default")
    game = env("GAME_TITLE", "Not set")
    
    status = f"""📊 Lambda Cut Status — v{local_ver}

🔹 Pipeline: {status_line}

📁 Files:
  📝 Scripts: {sc}
  🎬 Clips: {cc}
  🎤 TTS: {wc}
  📄 Transcripts: {tc}

⚙️ Config:
  🎤 Voice: {voice}
  🎵 Style: {style[:20]}...
  🎮 Game: {game}"""
    return status


def _get_files_list(folder):
    """Get list of files in a folder."""
    folder_map = {"scripts": SCRIPTS_DIR, "clips": SHORTS_DIR, "tts": TTS_DIR, "shorts": SHORTS_DIR}
    dir_path = folder_map.get(folder)
    if not dir_path:
        return "Unknown folder"
    
    files = sorted(glob.glob(os.path.join(dir_path, "*")), key=os.path.getmtime, reverse=True)[:10]
    if not files:
        return f"No files in {folder}"
    
    names = [os.path.basename(f) for f in files]
    return f"📁 {folder.capitalize()} ({len(names)} total):\n" + "\n".join(f"• {n[:40]}" for n in names)


def _do_update_menu():
    """Perform update and return result."""
    script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = perform_update(script_root)
    if result.get("success"):
        return f"✅ Updated to v{result.get('version', 'unknown')}. Restart listener to apply."
    return f"❌ Update failed: {result.get('error', 'Unknown error')}"

# ─── Helpers ───────────────────────────────────────────────────────────────────
def update_env_var(key, value):
    lines = []
    found = False
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            lines = f.readlines()
    with open(ENV_FILE, "w") as f:
        for line in lines:
            if line.strip().startswith(f"{key}="):
                f.write(f'{key}="{value}"\n')
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f'{key}="{value}"\n')
    ENV[key] = value

def retry(fn, attempts=3, delay=10, desc=""):
    for i in range(attempts):
        log(f"   Attempt {i+1}/{attempts}: {desc}")
        try:
            fn()
            return True
        except Exception as e:
            if i < attempts - 1:
                log(f"   Failed: {e}, retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
    return False

def count_files(pattern):
    return len(glob.glob(pattern))

def fmt_dur(seconds):
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    return f"{h}h {m}m"

def delete_partial_files():
    count = 0
    for pattern in ["*.part", "*.part-*.part", "*.ytdl", "*.f*.mp4.part"]:
        for d in [STREAMS_DIR, SCRIPTS_DIR, TTS_DIR, SHORTS_DIR]:
            for f in glob.glob(os.path.join(d, pattern)):
                os.remove(f)
                count += 1
    return count

def cleanup_all_files():
    count = 0
    for d in [STREAMS_DIR, TRANSCRIPTS_DIR, SCRIPTS_DIR, TTS_DIR, SHORTS_DIR]:
        for f in glob.glob(os.path.join(d, "*")):
            if os.path.isfile(f):
                os.remove(f)
                count += 1
    return count

def run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check, env=os.environ.copy())

# ─── Phase 1: Download ────────────────────────────────────────────────────────
def phase_download():
    set_status("Phase 1: Downloading video...")
    log("Phase 1: Downloading 1440p stream...")
    notify("Phase 1 Started: Downloading video...")

    playlist_url = env("PLAYLIST_URL")
    if not playlist_url:
        log_error("Phase 1 Failed: PLAYLIST_URL not configured")
        notify("Phase 1 Failed: PLAYLIST_URL not set in .env")
        set_status("Phase 1 FAILED")
        raise RuntimeError("PLAYLIST_URL not configured")

    cookies_ok = run(["yt-dlp", "--cookies-from-browser", "chrome", "--dump-single-json", "https://youtube.com"], check=False)
    if cookies_ok.returncode != 0:
        log_error("Phase 1 Failed: Chrome cookies not available. Run 'yt-dlp --cookies-from-browser chrome --dummy https://youtube.com' to create cookies.")
        notify("Phase 1 Failed: Chrome cookies not available")
        set_status("Phase 1 FAILED")
        raise RuntimeError("Chrome cookies not available")

    def do_dl():
        playlist_index = env("PLAYLIST_INDEX", "1")
        r = run(["yt-dlp", "--playlist-items", playlist_index,
                 "--cookies-from-browser", "chrome",
                 "-f", "bestvideo+bestaudio",
                 "-o", f"{STREAMS_DIR}/%(title)s.%(ext)s",
                 playlist_url])
        log(r.stdout[-500:] if r.stdout else "")
        if r.returncode != 0 and r.stderr:
            log_error(f"yt-dlp error: {r.stderr[-300:]}")

    if not retry(do_dl, 3, 10, "Download video"):
        log_error("Phase 1 failed after 3 attempts")
        notify("Phase 1 Failed: Download failed after 3 attempts")
        set_status("Phase 1 FAILED")
        raise RuntimeError("Phase 1 failed")

    video = find_video()
    if not video:
        log_error("Phase 1 Failed: No video file found after download")
        notify("Phase 1 Failed: No video downloaded")
        set_status("Phase 1 FAILED")
        raise RuntimeError("No video found after download")

    set_status("Phase 1 Complete")
    notify("Phase 1 Complete: Video downloaded")

# ─── Phase 2: Transcribe ──────────────────────────────────────────────────────
def phase_transcribe(video):
    if not video or not os.path.exists(video):
        log_error("Phase 2 Failed: Video file not found")
        notify("Phase 2 Failed: Video file not found")
        set_status("Phase 2 FAILED")
        raise RuntimeError("Video file not found")

    basename = os.path.splitext(os.path.basename(video))[0]
    json_file = os.path.join(TRANSCRIPTS_DIR, f"{basename}.json")

    if os.path.exists(json_file):
        log("Phase 2: Transcript exists, skipping")
        notify("Phase 2 Skipped (transcript exists)")
        return json_file

    set_status("Phase 2: Transcribing...")
    log("Phase 2: Transcribing...")
    
    transcription_success = False
    
    try:
        from faster_whisper import WhisperModel
        log("Using faster-whisper for transcription (primary, fastest)...")
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(video, language="en", vad_filter=True)
        srt_path = os.path.join(TRANSCRIPTS_DIR, f"{basename}.srt")
        json_path = os.path.join(TRANSCRIPTS_DIR, f"{basename}.json")
        
        def fmt_srt_time(seconds):
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"
        
        seg_list = []
        with open(srt_path, "w") as srt_f:
            sidx = 1
            for segment in segments:
                start = segment.start
                end = segment.end
                text = segment.text.strip()
                if text:
                    seg_list.append({"start": start, "end": end, "text": text})
                    srt_f.write(f"{sidx}\n")
                    srt_f.write(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n")
                    srt_f.write(f"{text}\n\n")
                    sidx += 1
        
        import json
        with open(json_path, "w") as json_f:
            json.dump({"segments": seg_list}, json_f)
        
        log("faster-whisper transcription complete")
        transcription_success = True
    except Exception as e:
        log(f"faster-whisper failed: {e}")
        
        if not transcription_success:
            try:
                import stable_whisper
                log("Falling back to stable-whisper...")
                model = stable_whisper.load_model("base")
                result = model.transcribe(video, language="en", vad=True)
                result.to_srt_vtt(os.path.join(TRANSCRIPTS_DIR, f"{basename}.srt"))
                result.save_as_json(os.path.join(TRANSCRIPTS_DIR, f"{basename}.json"))
                log("stable-whisper transcription complete")
                transcription_success = True
            except Exception as e2:
                log(f"stable-whisper failed: {e2}")
        
        if not transcription_success:
            log("Falling back to stable-ts CLI...")
            try:
                log(f"   stable-ts CLI: output_dir={TRANSCRIPTS_DIR}")
                r = run(["stable-ts", "-y", video, "--output_dir", TRANSCRIPTS_DIR,
                         "--output_format", "srt,json", "--word_timestamps", "False",
                         "--vad", "True", "--language", "en"], check=False)
                if r.stdout:
                    log(f"   stable-ts stdout: {r.stdout[-300:]}")
                if r.returncode != 0:
                    log_error(f"stable-ts CLI failed (exit {r.returncode}): {r.stderr[-300:] if r.stderr else 'Unknown error'}")
                else:
                    transcription_success = True
            except Exception as ts_e:
                log_error(f"stable-ts fallback also failed: {ts_e}")

    if not os.path.exists(json_file):
        log_error("Phase 2 Failed: Transcript file not created")
        notify("Phase 2 Failed: Transcription failed")
        set_status("Phase 2 FAILED")
        raise RuntimeError("Transcription failed")

    notify("Phase 2 Complete: Transcript generated")
    set_status("Phase 2 Complete")
    return json_file

# ─── Phase 3: Scripts ─────────────────────────────────────────────────────────

SCRIPT_PERSPECTIVES = [
    "Focus on the villain's motive — why did they do what they did?",
    "Focus on the hero's fatal mistake — what went wrong and why",
    "Focus on what the player/viewer missed — the hidden detail",
    "Focus on the cost of the outcome — who paid the real price",
    "Focus on the turning point — the one moment everything changed",
    "Focus on the emotional undercurrent — what the characters felt but never said",
    "Focus on the consequence — what happened after the dust settled",
    "Focus on the mystery — what remains unexplained",
    "Focus on the moral dilemma — what choices were made and why",
    "Focus on the ripple effect — how one event changed everything",
]

SCRIPT_VARIANTS = {
    "mystery_recap": {
        "style": "Mystery Recap",
        "voice_style": "Speak with intrigue and mystery. Drop hints naturally through sentences, not mysterious fragments. Build suspense through the story flow.",
        "instruction": """Write a mystery recap in complete, natural sentences. NO poetic fragments or mysterious one-liners. Tell the story chronologically while hinting at secrets. Start with the hook, build the clues naturally, end with an open question. Keep it 150-250 words.""",
    },
    "breakdown": {
        "style": "Breakdown",
        "voice_style": "Speak confidently and authoritatively. Explain causes and effects clearly, like an expert sharing knowledge.",
        "instruction": """Write an analytical breakdown. Explain WHY things happened, not just WHAT. Connect cause and effect in flowing paragraphs. Be authoritative and informative. Keep it 150-250 words.""",
    },
    "timeline": {
        "style": "Timeline",
        "voice_style": "Speak with urgency and forward momentum. Keep the story moving, build to the climax naturally.",
        "instruction": """Write a chronological timeline. Tell events in order from beginning to climax. Each sentence should flow naturally into the next. Build momentum through time progression. NO fragmented bullet points. Keep it 150-250 words.""",
    },
    "lesson": {
        "style": "Moral/Lesson",
        "voice_style": "Speak thoughtfully and reflectively. Like sharing wisdom with a friend, measured and genuine.",
        "instruction": """Write a reflective lesson. Explain what was learned and what could have been different. Use complete sentences that flow naturally. End with a thought-provoking question in sentence form. Keep it 150-250 words.""",
    },
    "narrative": {
        "style": "Narrative",
        "voice_style": "Speak naturally like telling a story to a friend. Conversational, engaging, keep the flow moving.",
        "instruction": """Write a first-person narrative as if you're telling a friend what happened. Use vivid but natural descriptions. Flow from one moment to the next. No bullet points or fragments. Keep it 150-250 words.""",
    },
    "news_report": {
        "style": "News Report",
        "voice_style": "Speak like a professional news reporter. Clear, factual, objective. Present information in order of importance.",
        "instruction": """Write a professional news report. Lead with the key fact, add context in flowing paragraphs. Use objective, factual language. NO dramatic fragments. Keep it 150-250 words.""",
    },
    "documentary": {
        "style": "Documentary",
        "voice_style": "Speak like a documentary host. Informed, warm, educational. Add context naturally.",
        "instruction": """Write a documentary-style narration. Add historical or psychological context naturally through flowing paragraphs. Inform and educate without being dry. Keep it 150-250 words.""",
    },
    "true_crime": {
        "style": "True Crime",
        "voice_style": "Speak with investigative intensity. Build tension through the story, pause for effect naturally.",
        "instruction": """Write a true crime story. Build investigation and tension through natural sentences. Tell what was discovered and how. Flow from discovery to revelation. Keep it 150-250 words.""",
    },
    "character_pov": {
        "style": "Character POV",
        "voice_style": "Speak as if you ARE the character. Personal, emotional, raw. First person, genuine.",
        "instruction": """Write from the main character's perspective. Show internal thoughts and feelings in first person. Make it personal and intimate. Flow from emotion to emotion naturally. Keep it 150-250 words.""",
    },
    "true_story": {
        "style": "True Story",
        "voice_style": "Speak like sharing an incredible story with a friend. Conversational, engaging, hook them early.",
        "instruction": """Write like you're sharing an amazing true story with a friend. Start with a hook, build naturally, end with impact. Conversational flow throughout. NO poetic fragments. Keep it 150-250 words.""",
    },
}

TTS_STYLE_OPTIONS = [
    "Speak with intrigue and mystery. Drop hints naturally through sentences, not mysterious fragments.",
    "Speak confidently and authoritatively. Explain causes and effects clearly, like an expert.",
    "Speak with urgency and forward momentum. Keep the story moving, build to the climax naturally.",
    "Speak thoughtfully and reflectively. Like sharing wisdom with a friend, measured and genuine.",
    "Speak naturally like telling a story to a friend. Conversational, engaging, keep the flow moving.",
    "Speak like a professional news reporter. Clear, factual, objective. Present information in order.",
    "Speak like a documentary host. Informed, warm, educational. Add context naturally.",
    "Speak with investigative intensity. Build tension through the story, pause for effect naturally.",
    "Speak as if you ARE the character. Personal, emotional, raw. First person, genuine.",
    "Speak like sharing an incredible story with a friend. Conversational, engaging, hook them early.",
]

def _build_script_prompt(variant_key, perspective, game_title):
    variant = SCRIPT_VARIANTS[variant_key]
    game_line = f"This is from the game {game_title}.\n\n" if game_title else ""

    return f"""You are a YouTube Shorts scriptwriter. {game_line}Style: {variant['style']}
Perspective: {perspective}

{variant['instruction']}

CRITICAL REQUIREMENT: You MUST write AT LEAST 200 words. This is the minimum acceptable length. Do not stop until you have written at least 200 words. Your output should be a complete, flowing narrative.

HARD RULES (never break these):
- NO dialogue — never write what anyone "said", "told", "asked", or "replied"
- NO first/second/third person narrator framing ("I saw", "the narrator says", "according to him")
- NO quotation marks anywhere
- NO parentheticals, stage directions, or annotations
- NO markdown formatting — plain text only
- NO phrases like "in conclusion", "to summarize", "the point is"
- NO abbreviations or symbols — spell everything out ("number one" not "#1", "dollars" not "$")
- Write ONLY facts and description as if narrating events directly

WRITING STYLE:
- Write in complete paragraphs, not fragments
- Every sentence should flow naturally into the next
- Avoid short one-sentence paragraphs
- The script should sound like natural human speech when read aloud
- Vary sentence length for natural rhythm

OUTPUT FORMAT (strict):
Line 1: TITLE: [6-10 word title, no punctuation, no clickbait caps]
Line 2: (blank)
Line 3+: The spoken script — pure text, no labels, no headers, no formatting

TITLE RULES:
- 6-10 words maximum
- No ALL CAPS words
- No exclamation marks or question marks
- Hint at the topic without spoiling the ending

REQUIREMENT: Script body MUST be at least 200 words. Write a complete, flowing narrative, not fragments.

Transcript:
{{transcript}}"""

def _rate_limit():
    now = time.time()
    last = 0
    try:
        with open(LAST_CALL) as f:
            last = float(f.read().strip())
    except (FileNotFoundError, ValueError):
        pass
    wait = 6 - (now - last)
    if wait > 0:
        time.sleep(wait)
    with open(LAST_CALL, "w") as f:
        f.write(str(time.time()))

def _gemini_script(text, script_num, keys_file):
    keys = get_gemini_keys()
    if not keys and os.path.exists(keys_file):
        with open(keys_file) as f:
            keys = [l.strip() for l in f if l.strip()]
    if not keys:
        raise RuntimeError("No API keys in keychain or gemini_keys.txt")

    variant_key, perspective = _get_next_round_robin()
    game_title = env("GAME_TITLE", "")
    prompt = _build_script_prompt(variant_key, perspective, game_title).format(transcript=text[:3000])
    log(f"   Variant: {SCRIPT_VARIANTS[variant_key]['style']}, Perspective: {perspective[:50]}...")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 3072}
    }).encode()

    start = (script_num - 1) % len(keys)
    for i in range(len(keys)):
        key = keys[(start + i) % len(keys)]
        log(f"   Trying key ...{key[-6:]}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={key}"
        for attempt in range(3):
            try:
                _rate_limit()
                req = urllib.request.Request(url, data=body,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    r = json.loads(resp.read())
                    return r["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep((2 ** attempt) * 15)
                else:
                    log(f"   HTTP {e.code} with key ...{key[-6:]}")
                    break
            except Exception as e:
                log(f"   Error: {e}")
                break
        log(f"   Key ...{key[-6:]} failed, next...")
    return None

def _extract_hour(json_file, start, end):
    with open(json_file) as f:
        data = json.load(f)
    parts = []
    for seg in data["segments"]:
        if seg["start"] >= start and seg["end"] <= end:
            t = re.sub(r"<[^>]*>", "", seg["text"]).strip()
            if t and len(t.split()) >= 3:
                parts.append(t)
    return "\n".join(parts)

def phase_scripts(json_file, duration, num_hours):
    if not json_file or not os.path.exists(json_file):
        log_error("Phase 3 Failed: Transcript file not found")
        notify("Phase 3 Failed: No transcript available")
        set_status("Phase 3 FAILED")
        raise RuntimeError("Transcript file not found")

    if not os.path.exists(KEYS_FILE):
        log_error("Phase 3 Failed: gemini_keys.txt not found")
        notify("Phase 3 Failed: No API keys configured")
        set_status("Phase 3 FAILED")
        raise RuntimeError("gemini_keys.txt not found")

    _init_round_robin(num_hours)
    
    set_status("Phase 3: Generating scripts...")
    log("Phase 3: Generating scripts (one per hour)...")
    notify(f"Phase 3 Started: Generating {num_hours} scripts...")
    delay = int(env("SCRIPT_DELAY", "300"))

    scripts_generated = 0
    for i in range(1, num_hours + 1):
        padded = f"{i:03d}"
        h_start = (i - 1) * 3600
        h_end   = min(i * 3600, duration)
        out     = os.path.join(SCRIPTS_DIR, f"script_{padded}.txt")

        if os.path.exists(out):
            log(f"   Skipping script {i} (exists)")
            continue

        try:
            log(f"   Processing hour {i}: {h_start}s - {h_end}s")
            text = _extract_hour(json_file, h_start, h_end)
            if not text:
                log(f"   Warning: No transcript for hour {i}, skipping")
                continue

            script = _gemini_script(text[:3000], i, KEYS_FILE)
            if script is None:
                log(f"   Warning: All keys failed for hour {i}, using raw transcript")
                script = text[:3000]

            with open(out, "w") as f:
                f.write(script)
            wc = len(script.split())
            log(f"   Script {i}: {wc} words")
            scripts_generated += 1
            set_status(f"Phase 3: Script {i}/{num_hours} generated")
            notify(f"Script {i}/{num_hours} generated ({wc} words)")
        except Exception as e:
            log_error(f"   Error generating script {i}: {e}")
            continue

        if i < num_hours:
            log(f"   Waiting {delay}s")
            time.sleep(delay)

    if scripts_generated == 0:
        log_error("Phase 3 Failed: No scripts were generated")
        notify("Phase 3 Failed: No scripts generated")
        set_status("Phase 3 FAILED")
        raise RuntimeError("No scripts generated")

    set_status("Phase 3 Complete")
    notify(f"Phase 3 Complete: {scripts_generated} scripts generated")

# ─── Phase 4: Clips ──────────────────────────────────────────────────────────
def _extract_scenes(json_file, h_start, h_end):
    scenes = []
    try:
        with open(json_file) as f:
            data = json.load(f)

        def clean(t):
            return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", t)).strip()

        entries = []
        for seg in data["segments"]:
            if seg["start"] < h_start or seg["end"] > h_end:
                continue
            t = clean(seg["text"])
            if len(t.split()) < 3:
                continue
            entries.append({"start": seg["start"], "end": seg["end"],
                            "text": t, "words": len(t.split())})

        if not entries:
            return scenes

        entries.sort(key=lambda x: x["start"])
        groups = [[entries[0]]]
        for j in range(1, len(entries)):
            gap = entries[j]["start"] - entries[j-1]["end"]
            dur = entries[j]["end"] - groups[-1][0]["start"]
            if gap <= 15 and dur <= 600:
                groups[-1].append(entries[j])
            else:
                groups.append([entries[j]])

        for grp in groups:
            words = sum(e["words"] for e in grp)
            dur = grp[-1]["end"] - grp[0]["start"]
            if words < 15 or dur < 30:
                continue
            density = words / max(dur, 1)
            txt = " ".join(e["text"] for e in grp)
            drama = txt.count("?") * 2 + txt.count("!") * 2
            score = words + density * 10 + drama
            scenes.append({
                "start": max(grp[0]["start"] - 5, h_start),
                "end": min(grp[-1]["end"] + 5, h_end),
                "score": score, "text": txt[:200]
            })

        scenes.sort(key=lambda x: x["score"], reverse=True)
    except Exception as e:
        log_error(f"Scene extraction: {e}")
    max_clips = int(env("CLIPS_PER_HOUR", "5"))
    return scenes[:max_clips]

def phase_clips(video, json_file, duration, num_hours):
    if not video or not os.path.exists(video):
        log_error("Phase 4 Failed: Video file not found")
        notify("Phase 4 Failed: Video file not found")
        set_status("Phase 4 FAILED")
        raise RuntimeError("Video file not found")

    if not json_file or not os.path.exists(json_file):
        log_error("Phase 4 Failed: Transcript file not found")
        notify("Phase 4 Failed: No transcript available")
        set_status("Phase 4 FAILED")
        raise RuntimeError("Transcript file not found")

    set_status("Phase 4: Generating clips...")
    log("Phase 4: Generating clips (scene-based)...")
    notify("Phase 4 Started: Generating clips...")
    vaapi = os.path.exists("/dev/dri/renderD128")
    log(f"   Encoding method: {'VAAPI' if vaapi else 'CPU (libx264)'}")

    ffmpeg_check = run(["ffmpeg", "-version"], check=False)
    if ffmpeg_check.returncode != 0:
        log_error("Phase 4 Failed: ffmpeg not available")
        notify("Phase 4 Failed: ffmpeg not installed")
        set_status("Phase 4 FAILED")
        raise RuntimeError("ffmpeg not available")

    clips_generated = 0
    for i in range(1, num_hours + 1):
        h_start = (i - 1) * 3600
        h_end   = min(i * 3600, duration)
        padded  = f"{i:03d}"

        scenes = _extract_scenes(json_file, h_start, h_end)
        if not scenes:
            log(f"   Hour {i}: No scenes found")
            continue

        for idx, sc in enumerate(scenes, 1):
            name = f"short_{padded}_{idx}.mp4"
            out  = os.path.join(SHORTS_DIR, name)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                log(f"   Skipping {name} (exists)")
                continue

            try:
                s, e = int(sc["start"]), int(sc["end"])
                dur  = e - s
                if dur <= 0:
                    log_error(f"   Skipping {name}: invalid duration ({dur}s)")
                    continue
                log(f"   Hour {i}, scene {idx}: {s}s-{e}s ({dur}s)")

                if vaapi:
                    cmd = ["ffmpeg", "-y",
                           "-vaapi_device", "/dev/dri/renderD128",
                           "-ss", str(s), "-i", video, "-t", str(dur),
                           "-vf", "format=nv12,hwupload",
                           "-c:v", "h264_vaapi", "-rc_mode", "CQP", "-global_quality", "10",
                           "-compression_level", "1",
                           "-af", "loudnorm",
                           "-c:a", "aac", "-b:a", "192k",
                           out]
                    enc = "VAAPI"
                else:
                    cmd = ["ffmpeg", "-y", "-ss", str(s), "-i", video, "-t", str(dur),
                           "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                           "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", out]
                    enc = "CPU"

                r = run(cmd, check=False)
                if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
                    log(f"   {name} created ({enc})")
                    clips_generated += 1
                else:
                    err_msg = r.stderr[-200:] if r.stderr else "Unknown error"
                    log_error(f"   Failed {name}: {err_msg}")
            except Exception as e:
                log_error(f"   Error creating {name}: {e}")
                continue

    if clips_generated == 0:
        log_error("Phase 4 Failed: No clips were generated")
        notify("Phase 4 Failed: No clips generated")
        set_status("Phase 4 FAILED")
        raise RuntimeError("No clips generated")

    set_status("Phase 4 Complete")
    notify(f"Phase 4 Complete: {clips_generated} clips generated")

# ─── Phase 5: TTS ─────────────────────────────────────────────────────────────
def _load_api_keys():
    keys_file = os.path.join(os.path.dirname(WORKSPACE), "gemini_keys.txt")
    if os.path.exists(keys_file):
        with open(keys_file) as f:
            return [line.strip() for line in f if line.strip()]
    return []

def _tts_api(text, out_pcm, voice, style, retries=3, delay=60):
    if style:
        text = f"{style} {text}"
    body = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}
        }
    }).encode()
    
    api_keys = _load_api_keys()
    if not api_keys:
        api_keys = [env("GEMINI_API_KEY")]
    
    time.sleep(2)  # Rate limit: 2 requests per second
    
    for key in api_keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    r = json.loads(resp.read())
                    audio = r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                    with open(out_pcm, "wb") as f:
                        f.write(base64.b64decode(audio))
                    return True
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < retries - 1:
                    wait = delay * (2 ** attempt)
                    log(f"   Key {key[:20]}... rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    log(f"   Key {key[:20]}... failed: {e.code}")
                    break
        log(f"   Switching to next API key...")
    
    return False

def _strip_title(script_text):
    lines = script_text.strip().split("\n")
    if lines and lines[0].startswith("TITLE:"):
        return "\n".join(lines[1:]).strip()
    return script_text.strip()

def phase_tts(duration, num_hours):
    voice = env("TTS_VOICE", "Vindemiatrix")
    if not voice:
        log_error("Phase 5 Failed: TTS_VOICE not configured")
        notify("Phase 5 Failed: TTS voice not set")
        set_status("Phase 5 FAILED")
        raise RuntimeError("TTS_VOICE not configured")

    api_key = env("GEMINI_API_KEY")
    if not api_key:
        log_error("Phase 5 Failed: GEMINI_API_KEY not configured")
        notify("Phase 5 Failed: No API key configured")
        set_status("Phase 5 FAILED")
        raise RuntimeError("GEMINI_API_KEY not configured")

    # Initialize round-robin for TTS voices and styles (shuffled once per run)
    # Already initialized in phase_scripts, just ensure it's ready
    if not _rr_voices:
        _init_round_robin(num_hours)
    
    set_status("Phase 5: Generating TTS...")
    log("Phase 5: Generating TTS...")
    notify("Phase 5 Started: Generating TTS...")
    delay = int(env("TTS_DELAY", "120"))

    tts_generated = 0
    for i in range(1, num_hours + 1):
        padded = f"{i:03d}"
        wav = os.path.join(TTS_DIR, f"tts_{padded}.wav")
        srt = os.path.join(TTS_DIR, f"tts_{padded}.srt")
        script_file = os.path.join(SCRIPTS_DIR, f"script_{padded}.txt")

        if not os.path.exists(wav):
            if not os.path.exists(script_file):
                log(f"   Warning: Script {i} not found, skipping TTS")
                continue
            log(f"   Generating TTS for script {i}...")
            try:
                with open(script_file) as f:
                    txt = f.read()
                if not txt.strip():
                    log_error(f"   Warning: Script {i} is empty, skipping")
                    continue

                pcm = os.path.join(TTS_DIR, f"tts_{padded}.pcm")
                tts_text = _strip_title(txt)
                
                # Use round-robin voice and style
                rr_voice, rr_style = _get_next_voice_style()
                log(f"   Using voice: {rr_voice}, style: {rr_style[:40]}...")
                
                _tts_api(tts_text, pcm, rr_voice, rr_style)

                if not os.path.exists(pcm):
                    log_error(f"   TTS API call failed for script {i}")
                    continue

                r = run(["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1",
                         "-i", pcm, "-ar", "44100", "-ac", "2", wav], check=False)
                if r.returncode != 0:
                    log_error(f"   ffmpeg failed for script {i}: {r.stderr[-200:] if r.stderr else 'Unknown'}")
                    continue
                
                if os.path.exists(pcm):
                    os.remove(pcm)
                log(f"   tts_{padded}.wav created")
                tts_generated += 1
                set_status(f"Phase 5: TTS {i}/{num_hours} generated")
                notify(f"TTS {i}/{num_hours} generated")
            except Exception as e:
                log_error(f"   Error generating TTS for script {i}: {e}")
                continue
        else:
            log(f"   TTS {i} WAV exists, skipping")

        if not os.path.exists(srt):
            if not os.path.exists(wav):
                log(f"   Warning: Cannot generate SRT, WAV not found for script {i}")
            else:
                log(f"   Generating SRT for tts_{padded}.wav...")
                srt_out = os.path.splitext(wav)[0] + ".srt"
                try:
                    from faster_whisper import WhisperModel
                    model = WhisperModel("base", device="cpu", compute_type="int8")
                    segments, _ = model.transcribe(wav, language="en", vad_filter=True)
                    with open(srt_out, "w") as f:
                        for idx, seg in enumerate(segments, 1):
                            start, end, text = seg.start, seg.end, seg.text.strip()
                            if text:
                                f.write(f"{idx}\n")
                                f.write(f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},000 --> {int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},000\n")
                                f.write(f"{text}\n\n")
                    log(f"   tts_{padded}.srt created (faster-whisper)")
                except Exception as e:
                    log_error(f"   SRT failed for tts_{padded}: {e}")
        else:
            log(f"   tts_{padded}.srt exists, skipping")

        if i < num_hours:
            log(f"   Waiting {delay}s")
            time.sleep(delay)

    if tts_generated == 0:
        log_error("Phase 5 Failed: No TTS files were generated")
        notify("Phase 5 Failed: No TTS generated")
        set_status("Phase 5 FAILED")
        raise RuntimeError("No TTS generated")

    set_status("Phase 5 Complete")
    notify(f"Phase 5 Complete: {tts_generated} TTS files generated")

# ─── Find latest video ────────────────────────────────────────────────────────
def find_video():
    for ext in ("*.webm", "*.mp4", "*.mkv"):
        files = sorted(glob.glob(os.path.join(STREAMS_DIR, ext)),
                       key=os.path.getmtime, reverse=True)
        if files:
            return files[0]
    return None

def video_info(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path])
    return int(float(r.stdout.strip()))

# ─── Local Recording Processing ──────────────────────────────────────────────
def run_local_recordings(recording_path):
    """Process local recordings from a directory."""
    global PIPELINE_STOP_REQUESTED, PIPELINE_RUNNING
    PIPELINE_STOP_REQUESTED = False
    PIPELINE_RUNNING = True

    def check_stop():
        if PIPELINE_STOP_REQUESTED:
            log("Pipeline stopped by user")
            set_status("Pipeline Stopped")
            notify("Pipeline stopped by user.")
            return True
        return False

    # Create required directories
    for d in (STREAMS_DIR, TRANSCRIPTS_DIR, SCRIPTS_DIR, TTS_DIR, SHORTS_DIR, OUTPUT_DIR):
        os.makedirs(d, exist_ok=True)

    # Check if recording path exists
    if not os.path.exists(recording_path):
        log_error(f"Recording path not found: {recording_path}")
        notify(f"Error: Recording path not found: {recording_path}")
        return

    # Find all video files in recording path
    video_extensions = (".mp4", ".mkv", ".webm", ".avi", ".mov")
    video_files = []
    for f in os.listdir(recording_path):
        if f.lower().endswith(video_extensions):
            full_path = os.path.join(recording_path, f)
            video_files.append(full_path)

    if not video_files:
        log_error(f"No video files found in {recording_path}")
        notify(f"No video files found in {recording_path}")
        return

    # Sort by modification time (oldest first)
    video_files.sort(key=os.path.getmtime)

    log(f"Found {len(video_files)} local recording(s)")
    notify(f"Processing {len(video_files)} local recording(s)...")

    # Process each video
    for i, video_file in enumerate(video_files, 1):
        if check_stop():
            return

        video_name = os.path.basename(video_file)
        log(f"Processing video {i}/{len(video_files)}: {video_name}")

        # Copy video to streams directory
        dest_path = os.path.join(STREAMS_DIR, video_name)
        if not os.path.exists(dest_path):
            shutil.copy2(video_file, dest_path)
            log(f"  Copied to streams/: {video_name}")

        # Run the pipeline phases for this video
        try:
            duration = video_info(dest_path)
            if duration <= 0:
                log_error(f"Invalid video: {video_name}")
                continue

            num_hours = max(1, duration // 3600)
            log(f"Video: {duration}s = {num_hours} hour(s)")

            # Phase 2: Transcribe
            json_file = phase_transcribe(dest_path)
            if check_stop(): return

            # Phase 3: Scripts
            if json_file:
                phase_scripts(json_file, duration, num_hours)
                if check_stop(): return

            # Phase 4: Clips
            if json_file:
                phase_clips(dest_path, json_file, duration, num_hours)
                if check_stop(): return

            # Phase 5: TTS
            phase_tts(duration, num_hours)
            if check_stop(): return

            log(f"Video {i}/{len(video_files)} complete!")

            # Delay between videos (300 seconds)
            if i < len(video_files):
                log("Waiting 300 seconds before next video...")
                time.sleep(300)

        except Exception as e:
            log_error(f"Error processing {video_name}: {e}")
            continue

    log("All local recordings processed!")
    set_status("Pipeline Complete")
    notify(f"Local recording pipeline complete! Processed {len(video_files)} video(s).")

# ─── Pipeline orchestrator ────────────────────────────────────────────────────
def run_pipeline(skip=None, phases=None):
    global PIPELINE_STOP_REQUESTED
    PIPELINE_STOP_REQUESTED = False

    def check_stop():
        if PIPELINE_STOP_REQUESTED:
            log("Pipeline stopped by user")
            set_status("Pipeline Stopped")
            notify("Pipeline stopped by user.")
            return True
        return False

    for d in (STREAMS_DIR, TRANSCRIPTS_DIR, SCRIPTS_DIR, TTS_DIR, SHORTS_DIR, OUTPUT_DIR):
        os.makedirs(d, exist_ok=True)

    skip = skip or set()
    if phases:
        skip = {1,2,3,4,5} - set(phases)

    if 1 not in skip:
        phase_download()
        if check_stop(): return

    video = find_video()
    if not video:
        log_error("No video found in streams/")
        return
    duration = video_info(video)
    log(f"Target: {os.path.basename(video)} ({duration}s)")

    if 2 not in skip:
        json_file = phase_transcribe(video)
        if check_stop(): return
    else:
        json_file = sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.json")),
                key=os.path.getmtime, reverse=True)[0] \
           if glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.json")) else None

    num_hours = max(1, duration // 3600)
    log(f"Video: {duration}s = {num_hours} hour(s)")

    if 3 not in skip and json_file:
        phase_scripts(json_file, duration, num_hours)
        if check_stop(): return
    elif 3 not in skip:
        log_error("No transcript for script generation")

    if 4 not in skip and json_file:
        phase_clips(video, json_file, duration, num_hours)
        if check_stop(): return
    elif 4 not in skip:
        log_error("No transcript for clip generation")

    if 5 not in skip:
        phase_tts(duration, num_hours)
        if check_stop(): return

    log("Pipeline Complete!")
    set_status("Pipeline Complete")

    sc = count_files(os.path.join(SCRIPTS_DIR, "*.txt"))
    cc = count_files(os.path.join(SHORTS_DIR, "*.mp4"))
    tw = count_files(os.path.join(TTS_DIR, "*.wav"))
    ts = count_files(os.path.join(TTS_DIR, "*.srt"))
    tc = count_files(os.path.join(TRANSCRIPTS_DIR, "*.json"))

    notify(f"""Pipeline Complete!

Video: {os.path.basename(video)}
Duration: {fmt_dur(duration)}

Created Files:
Scripts: {sc}
Clips: {cc}
TTS WAVs: {tw}
TTS SRTs: {ts}
Transcripts: {tc}

Total output files: {sc + cc + tw + ts}""")

# ─── Telegram Listener ────────────────────────────────────────────────────────
def tg_api(method, params=None):
    token = env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data, method="POST")
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read())

def process_cmd(text, chat_id):
    parts = text.split(None, 1)
    cmd  = parts[0].split("@", 1)[0]
    args = parts[1] if len(parts) > 1 else ""

    if cmd in ("/run_pipeline", "/runpipeline"):
        if not _check_configured():
            tg_send("Not configured yet. Run onboarding first:\n  python3 lambda_cut.py onboard")
        else:
            tg_send("Pipeline triggered! Source: YouTube playlist")
            def _run():
                global PIPELINE_RUNNING
                PIPELINE_RUNNING = True
                try:
                    run_pipeline()
                except Exception as e:
                    tg_send(f"Pipeline error: {e}")
                finally:
                    PIPELINE_RUNNING = False
            threading.Thread(target=_run, daemon=True).start()

    elif cmd in ("/run_local", "/runlocal"):
        if not _check_configured():
            tg_send("Not configured yet. Run onboarding first:\n  python3 lambda_cut.py onboard")
        else:
            recording_path = env("RECORDING_PATH", os.path.expanduser("~/Videos/Recordings"))
            tg_send(f"Current source: YouTube playlist (default)\nProcessing local recordings from: {recording_path}")
            def _run():
                global PIPELINE_RUNNING
                PIPELINE_RUNNING = True
                try:
                    run_local_recordings(recording_path)
                except Exception as e:
                    tg_send(f"Local recording error: {e}")
                finally:
                    PIPELINE_RUNNING = False
            threading.Thread(target=_run, daemon=True).start()

    elif cmd in ("/run_phase", "/runphase"):
        if not _check_configured():
            tg_send("Not configured yet. Run onboarding first:\n  python3 lambda_cut.py onboard")
        elif not args:
            tg_send("Usage: /run_phase 5 or /run_phase 2,3")
        else:
            phases = [int(p) for p in args.split(",")]
            tg_send(f"Pipeline triggered! Phases: {phases}")
            def _run():
                global PIPELINE_RUNNING
                PIPELINE_RUNNING = True
                try:
                    run_pipeline(phases=phases)
                except Exception as e:
                    tg_send(f"Pipeline error: {e}")
                finally:
                    PIPELINE_RUNNING = False
            threading.Thread(target=_run, daemon=True).start()

    elif cmd in ("/skip_phase", "/skipphase"):
        if not _check_configured():
            tg_send("Not configured yet. Run onboarding first:\n  python3 lambda_cut.py onboard")
        elif not args:
            tg_send("Usage: /skip_phase 1 or /skip_phase 1,2")
        else:
            skip = {int(p) for p in args.split(",")}
            tg_send(f"Pipeline triggered! Skipping: {skip}")
            def _run():
                global PIPELINE_RUNNING
                PIPELINE_RUNNING = True
                try:
                    run_pipeline(skip=skip)
                except Exception as e:
                    tg_send(f"Pipeline error: {e}")
                finally:
                    PIPELINE_RUNNING = False
            threading.Thread(target=_run, daemon=True).start()

    elif cmd in ("/set_voice", "/setvoice"):
        if not args:
            tg_send("Usage: /set_voice Algenib\nGemini Voices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat, Achernar, Alnilam, Laomedeia")
        else:
            update_env_var("TTS_VOICE", args)
            tg_send(f"Voice set to: {args}")

    elif cmd in ("/voices", "/listvoices"):
        tg_send("""Gemini TTS Voices (Chirp 3):

Female: Vindemiatrix, Aoede, Callirrhoe, Gacrux, Sulafat, Leda, Kore, Enceladus, Erinome, Despina, Alnilam, Laomedeia, Achernar, Pulcherrima, Zephyr
Male: Puck, Charon, Fenrir, Orus, Iapetus, Umbriel, Algieba, Rasalgethi, Schedar, Sadachbia, Sadaltager, Achird, Zubenelgenubi, Algenib, Autonoe

Random voice selection is enabled - voice rotates on each listener restart.
Use /set_voice <name> to select a specific voice.
Example: /set_voice Vindemiatrix""")

    elif cmd in ("/set_style", "/setstyle"):
        if not args:
            update_env_var("TTS_STYLE", "")
            tg_send("Style cleared.")
        else:
            update_env_var("TTS_STYLE", args)
            tg_send(f"Style set to: {args}")

    elif cmd in ("/set_index", "/setindex"):
        if not args:
            update_env_var("PLAYLIST_INDEX", "")
            tg_send("Playlist index reset to default (1).")
        else:
            try:
                idx = int(args)
                if idx < 1:
                    tg_send("Index must be 1 or greater.")
                else:
                    update_env_var("PLAYLIST_INDEX", str(idx))
                    tg_send(f"Playlist index set to: {idx}")
            except ValueError:
                tg_send("Invalid index. Use /set_index 3")

    elif cmd in ("/set_clips", "/setclips"):
        if not args:
            current = env("CLIPS_PER_HOUR", "5")
            tg_send(f"Current clips per hour: {current}\nUsage: /set_clips 10")
        else:
            try:
                clips = int(args)
                if clips < 1 or clips > 20:
                    tg_send("Clips per hour must be between 1 and 20.")
                else:
                    update_env_var("CLIPS_PER_HOUR", str(clips))
                    tg_send(f"Clips per hour set to: {clips}")
            except ValueError:
                tg_send("Invalid number. Use /set_clips 10")

    elif cmd in ("/set_game", "/setgame"):
        if not args:
            current = env("GAME_TITLE", "")
            if current:
                tg_send(f"Current game: {current}\nUsage: /set_game The Last of Us Part II\nClear with: /set_game clear")
            else:
                tg_send("No game set.\nUsage: /set_game The Last of Us Part II")
        elif args.lower() == "clear":
            update_env_var("GAME_TITLE", "")
            tg_send("Game title cleared.")
        else:
            update_env_var("GAME_TITLE", args)
            tg_send(f"Game set to: {args}")

    elif cmd in ("/config", "/settings"):
        voice = env("TTS_VOICE", "Vindemiatrix")
        style = env("TTS_STYLE") or "(none)"
        index = env("PLAYLIST_INDEX", "1")
        clips = env("CLIPS_PER_HOUR", "5")
        game = env("GAME_TITLE", "") or "(none)"
        status = "Running" if PIPELINE_RUNNING else "Idle"

        wc = count_files(os.path.join(WORKSPACE, "tts/*.wav"))
        sc = count_files(os.path.join(WORKSPACE, "tts/*.srt"))
        rc = count_files(os.path.join(WORKSPACE, "scripts/*.txt"))
        cc = count_files(os.path.join(WORKSPACE, "shorts/*.mp4"))
        tg_send(f"Config:\nGame: {game}\nVoice: {voice}\nStyle: {style}\nIndex: {index}\nClips/hr: {clips}\nStatus: {status}\n\nFiles:\nScripts: {rc}\nClips: {cc}\nTTS WAVs: {wc}\nTTS SRTs: {sc}")

    elif cmd == "/status":
        listener_status = "No"
        listener_pid = "-"
        listener_dir = "-"
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)
                    listener_status = "Yes"
                    listener_pid = str(pid)
                    listener_dir = os.readlink(f"/proc/{pid}/cwd")
                except (ProcessLookupError, PermissionError):
                    os.remove(PID_FILE)
            except (ValueError, OSError):
                pass

        s = open(STATUS_FILE).read() if os.path.exists(STATUS_FILE) else ""
        pipeline_status = f"Running: {s}" if PIPELINE_RUNNING else f"Idle. Last: {s}" if s else "Idle"
        
        # Get version and update status
        script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_ver = get_local_version(script_root)
        update_info = check_for_updates(script_root)
        update_status = ""
        if update_info.get("update_available"):
            remote_ver = update_info.get("remote_version", "?")
            update_status = f"\n\nUpdate: v{remote_ver} available ✨"

        tg_send(f"Listener: {listener_status}\nPID: {listener_pid}\nDir: {listener_dir}\nVersion: v{local_ver}\n\nPipeline: {pipeline_status}{update_status}")

    elif cmd == "/debug":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                lines = f.readlines()[-10:]
            important = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if len(line) > 150:
                    continue
                if "Transcribe:" in line or "transcribing" in line.lower():
                    continue
                important.append(line)
            if important:
                txt = "\n".join(important[-8:])
                tg_send(f"🐛 Recent Log:\n\n{txt}")
            else:
                tg_send("No recent log entries.")
        else:
            tg_send("No logs found.")


    elif cmd == "/help":
        tg_send("""Lambda Cut — YouTube Shorts Pipeline
Converts long-form YouTube videos into shorts with AI scripts and TTS.

Pipeline Phases:
1️⃣ Download  - Download latest video (best quality)
2️⃣ Transcribe - Generate transcript with stable-ts
3️⃣ Scripts   - AI-generated short scripts via Gemini
4️⃣ Clips    - Extract video clips based on scenes
5️⃣ TTS       - Generate narration audio + subtitles

Commands:
/run_pipeline    - Run full pipeline
/run_local       - Run pipeline on local recording
/run_phase 5    - Run specific phase(s)
/run_phase 2,3  - Run phases 2 and 3
/skip_phase 1,2 - Skip specific phases

/set_voice Puck    - Change TTS voice
/voices          - List available voices
/set_style Say...  - Set style prefix
/set_style         - Clear style
/set_index 3      - Set playlist index (1=first video)
/set_clips 10     - Set clips per hour (1-20)
/set_game Title   - Set game title for scripts
/set_game clear   - Clear game title

/config     - Settings and file counts
/status     - Listener and pipeline status
/debug      - Show recent debug log entries

/version    - Show current version
/update     - Check for and install updates

/restart_listener - Restart the listener
/stop_pipeline   - Stop running pipeline

/delete_partial  - Delete incomplete files
/cleanup         - Delete all generated files
/clean_backups  - Clean old backup versions

/menu      - Show interactive inline menu
/help - This message""")

    elif cmd == "/menu":
        main_menu = get_main_menu()
        tg_send_menu("📋 Lambda Cut Menu — Select an action:", main_menu)

    elif cmd in ("/restart_listener", "/restart"):
        tg_send("Restarting listener via systemd...")
        subprocess.run(["systemctl", "--user", "restart", "lambda-cut-listener.service"], capture_output=True)

    elif cmd == "/stop_pipeline":
        if PIPELINE_RUNNING:
            global PIPELINE_STOP_REQUESTED
            PIPELINE_STOP_REQUESTED = True
            tg_send("Pipeline stop requested. Finishing current phase...")
        else:
            tg_send("No pipeline is currently running.")

    elif cmd == "/delete_partial":
        count = delete_partial_files()
        tg_send(f"Deleted {count} partial file(s).")

    elif cmd == "/cleanup":
        count = cleanup_all_files()
        tg_send(f"Deleted {count} file(s) from all output directories.")

    elif cmd == "/clean_backups":
        cleanup_old_backups(WORKSPACE)
        tg_send("Old backups cleaned up.")

    elif cmd == "/version":
        script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_ver = get_local_version(script_root)
        update_info = check_for_updates(script_root)
        remote_ver = update_info.get("remote_version", "Unknown")
        if update_info.get("update_available"):
            tg_send(f"Current version: v{local_ver}\nLatest version: v{remote_ver}\n\nUpdate available! Run /update to install.")
        else:
            tg_send(f"Current version: v{local_ver}\nLatest version: v{remote_ver or 'Unknown'}\n\nYou're up to date!")

    elif cmd == "/update":
        script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        update_info = check_for_updates(script_root)
        
        if not update_info.get("update_available"):
            tg_send("No update available. You're on the latest version!")
        else:
            remote_ver = update_info.get("remote_version", "Unknown")
            release_notes = get_release_notes()
            # Truncate release notes if too long
            if len(release_notes) > 500:
                release_notes = release_notes[:500] + "..."
            
            tg_send(f"""Update Available: v{remote_ver}

Release Notes:
{release_notes[:500]}

This will:
1. Backup current installation (up to 2 backups)
2. Download and install new files
3. Preserve your .env and settings
4. Restart listener

Type /confirm_update to proceed.""")
    
    elif cmd == "/confirm_update":
        script_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tg_send("Updating... Please wait.")
        
        def _update():
            global LISTENER_RESTART
            result = perform_update(script_root)
            if result.get("success"):
                tg_send(f"✅ {result.get('message')}\n\nRestarting listener...")
                time.sleep(1)
                LISTENER_RESTART = True
            else:
                tg_send(f"❌ {result.get('message')}")
        
        t = threading.Thread(target=_update)
        t.start()
        t.join()  # Wait for update to complete before continuing

    else:
        tg_send("Unknown command. Use /help for available commands.")

def listen():
    global LISTENER_RESTART
    
    if not _telegram_configured():
        print("Telegram not configured. Run onboard and enable Telegram to use the listener.")
        sys.exit(1)

    script_path = os.path.abspath(__file__)
    workspace = os.path.dirname(os.path.dirname(script_path))

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                os.kill(old_pid, 15)
                time.sleep(1)
                try:
                    os.kill(old_pid, 0)
                    os.kill(old_pid, 9)
                except ProcessLookupError:
                    pass
                print(f"Stopped existing listener (PID {old_pid})")
                tg_send(f"Stopped existing listener (PID {old_pid}). Starting new listener.")
            except ProcessLookupError:
                pass
        except (ValueError, OSError):
            pass
        try:
            os.remove(PID_FILE)
        except OSError:
            pass

    svc_dir = os.path.expanduser("~/.config/systemd/user")
    svc_file = os.path.join(svc_dir, "lambda-cut-listener.service")
    if os.path.exists(svc_file):
        with open(svc_file) as f:
            svc_content = f.read()
        python = sys.executable
        new_svc = f"""[Unit]
Description=Lambda Cut Telegram Listener
After=network.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 10
ExecStart={python} {script_path} listen
WorkingDirectory={workspace}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""
        if svc_content != new_svc:
            with open(svc_file, "w") as f:
                f.write(new_svc)
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            print(f"Updated systemd service to point to {workspace}")
            tg_send(f"Systemd service updated to point to {workspace}")

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    env("TELEGRAM_BOT_TOKEN")  # Ensure token is loaded
    chat  = env("TELEGRAM_CHAT_ID")

    global STREAMING
    STREAMING = True

    me = tg_api("getMe")
    print(f"Lambda Cut Listener — @{me['result']['username']}")
    
    # Check for updates
    print("Checking for updates...")
    script_root = os.path.dirname(os.path.dirname(script_path))
    update_info = check_for_updates(script_root)
    local_ver = update_info.get("local_version", "Unknown")
    print(f"Version: v{local_ver}")
    
    if update_info.get("update_available"):
        remote_ver = update_info.get("remote_version", "Unknown")
        print(f"Update available: v{remote_ver}")
        tg_send(f"🔔 Update available: v{remote_ver}\nRun /update to install.")
    else:
        print("No updates available.")

    # Rotate TTS voice on each listener start (all voices - male and female)
    all_voices = [
        "Vindemiatrix", "Aoede", "Callirrhoe", "Gacrux", "Sulafat", "Leda",
        "Kore", "Enceladus", "Erinome", "Despina", "Alnilam", "Laomedeia",
        "Achernar", "Pulcherrima", "Zephyr", "Puck", "Charon", "Fenrir",
        "Orus", "Iapetus", "Umbriel", "Algieba", "Rasalgethi", "Schedar",
        "Sadachbia", "Sadaltager", "Achird", "Zubenelgenubi", "Algenib", "Autonoe"
    ]
    rotated_voice = random.choice(all_voices)
    
    # Also rotate TTS style randomly
    rotated_style = random.choice(TTS_STYLE_OPTIONS)
    update_env_var("TTS_VOICE", rotated_voice)
    update_env_var("TTS_STYLE", rotated_style)
    print(f"Voice rotated to: {rotated_voice}")
    print(f"Style rotated to: {rotated_style[:50]}...")

    tg_send(f"Lambda Cut listener started (v{local_ver}).\nVoice: {rotated_voice}\nStyle: {rotated_style[:50]}...")
    offset = 0
    if os.path.exists(OFFSET_FILE):
        try:
            offset = int(open(OFFSET_FILE).read().strip())
        except (ValueError, OSError):
            pass

    global LISTENER_RUNNING
    while LISTENER_RUNNING:
        try:
            r = tg_api("getUpdates", {"limit": 3, "timeout": 30, "offset": offset})
            if not r.get("ok"):
                time.sleep(5)
                continue
            for upd in r["result"]:
                offset = upd["update_id"] + 1
                with open(OFFSET_FILE, "w") as f:
                    f.write(str(offset))
                
                # Handle callback_query (menu button clicks)
                cb = upd.get("callback_query", {})
                if cb:
                    cb_id = cb.get("id", "")
                    cb_data = cb.get("data", "")
                    cb_msg = cb.get("message", {})
                    cb_chat = str(cb_msg.get("chat", {}).get("id", ""))
                    
                    if cb_chat == str(chat) and cb_data:
                        print(f"Callback: {cb_data}")
                        result = handle_menu_callback(cb_data)
                        
                        if result:
                            if isinstance(result, tuple):
                                response_text, action_or_markup = result
                            else:
                                response_text = result
                                action_or_markup = None
                            
                            # Answer the callback to dismiss loading spinner
                            if response_text:
                                tg_answer_callback(cb_id, response_text[:200])
                            
                            # If there's a keyboard markup to show, update the message
                            if isinstance(action_or_markup, dict):
                                token = env("TELEGRAM_BOT_TOKEN")
                                if token:
                                    msg_id = cb_msg.get("message_id", "")
                                    try:
                                        text = response_text if response_text else "📋 Select option:"
                                        params = {"chat_id": cb_chat, "message_id": msg_id, "text": text, "reply_markup": json.dumps(action_or_markup)}
                                        data = urllib.parse.urlencode(params).encode()
                                        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/editMessageText", data=data, method="POST")
                                        urllib.request.urlopen(req, timeout=10)
                                    except Exception as e:
                                        print(f"Menu update error: {e}")
                            elif action_or_markup == "run_pipeline":
                                tg_send("▶️ Running full pipeline...")
                                def _run():
                                    global PIPELINE_RUNNING
                                    PIPELINE_RUNNING = True
                                    try:
                                        run_pipeline()
                                    except Exception as e:
                                        tg_send(f"Pipeline error: {e}")
                                    finally:
                                        PIPELINE_RUNNING = False
                                threading.Thread(target=_run, daemon=True).start()
                            elif action_or_markup == "restart_listener":
                                tg_answer_callback(cb_id, "Restarting...")
                                tg_send("Restarting listener via systemd...")
                                subprocess.run(["systemctl", "--user", "restart", "lambda-cut-listener.service"], capture_output=True)
                            elif action_or_markup == "stop_pipeline":
                                global PIPELINE_STOP_REQUESTED
                                PIPELINE_STOP_REQUESTED = True
                                tg_answer_callback(cb_id, "Pipeline stop requested")
                                tg_send("Pipeline stop requested. Finishing current phase...")
                            elif action_or_markup == "run_phase 1":
                                tg_answer_callback(cb_id, "Running Phase 1...")
                                def _run_p1():
                                    global PIPELINE_RUNNING; PIPELINE_RUNNING = True
                                    try: run_pipeline(phases=[1])
                                    except Exception as e: tg_send(f"Phase 1 error: {e}")
                                    finally: PIPELINE_RUNNING = False
                                threading.Thread(target=_run_p1, daemon=True).start()
                            elif action_or_markup == "run_phase 3":
                                tg_answer_callback(cb_id, "Running Phase 3...")
                                def _run_p3():
                                    global PIPELINE_RUNNING; PIPELINE_RUNNING = True
                                    try: run_pipeline(phases=[3])
                                    except Exception as e: tg_send(f"Phase 3 error: {e}")
                                    finally: PIPELINE_RUNNING = False
                                threading.Thread(target=_run_p3, daemon=True).start()
                            elif action_or_markup == "run_phase 4":
                                tg_answer_callback(cb_id, "Running Phase 4...")
                                def _run_p4():
                                    global PIPELINE_RUNNING; PIPELINE_RUNNING = True
                                    try: run_pipeline(phases=[4])
                                    except Exception as e: tg_send(f"Phase 4 error: {e}")
                                    finally: PIPELINE_RUNNING = False
                                threading.Thread(target=_run_p4, daemon=True).start()
                            elif action_or_markup == "run_phase 5":
                                tg_answer_callback(cb_id, "Running Phase 5...")
                                def _run_p5():
                                    global PIPELINE_RUNNING; PIPELINE_RUNNING = True
                                    try: run_pipeline(phases=[5])
                                    except Exception as e: tg_send(f"Phase 5 error: {e}")
                                    finally: PIPELINE_RUNNING = False
                                threading.Thread(target=_run_p5, daemon=True).start()
                            elif isinstance(action_or_markup, dict):
                                # It's a new keyboard markup - edit the message
                                token = env("TELEGRAM_BOT_TOKEN")
                                if token and response_text:
                                    msg_id = cb_msg.get("message_id", "")
                                    try:
                                        params = {"chat_id": cb_chat, "message_id": msg_id, "text": response_text, "reply_markup": json.dumps(action_or_markup)}
                                        data = urllib.parse.urlencode(params).encode()
                                        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/editMessageText", data=data, method="POST")
                                        urllib.request.urlopen(req, timeout=10)
                                    except Exception as e:
                                        print(f"Menu update error: {e}")
                        continue
                
                # Handle regular message commands
                msg = upd.get("message", {})
                cid = str(msg.get("chat", {}).get("id", ""))
                txt = msg.get("text", "")
                if cid == str(chat) and txt:
                    print(f"Received: {txt}")
                    process_cmd(txt, cid)
                    if LISTENER_RESTART:
                        LISTENER_RESTART = False
                        tg_send("Restarting listener via systemd...")
                        subprocess.run(["systemctl", "--user", "restart", "lambda-cut-listener.service"], capture_output=True)
                        sys.exit(0)
        except urllib.error.URLError:
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

    tg_send("Lambda Cut listener stopped.")

# ─── Onboard ──────────────────────────────────────────────────────────────────
def onboard():
    G = "\033[32m"; R = "\033[31m"; Y = "\033[33m"; B = "\033[1m"; X = "\033[0m"
    ok = lambda: f"{G}\u2713{X}"
    fail = lambda: f"{R}\u2717{X}"
    warn = lambda: f"{Y}!{X}"

    print(f"\n{B}{'='*40}")
    print(f" Lambda Cut — Setup")
    print(f"{'='*40}{X}\n")

    # ── Installation directory ──
    print(f"{B}Installation directory{X}")
    print(f"  Default: {DEFAULT_WORKSPACE}")
    ws = input(f"  Path [{DEFAULT_WORKSPACE}]: ").strip()
    workspace = os.path.expanduser(ws) if ws else DEFAULT_WORKSPACE

    # Create directory structure
    wf_dir = os.path.join(workspace, "workflows")
    for d in (workspace, wf_dir,
              os.path.join(workspace, "streams"),
              os.path.join(workspace, "transcripts"),
              os.path.join(workspace, "scripts"),
              os.path.join(workspace, "tts"),
              os.path.join(workspace, "shorts")):
        os.makedirs(d, exist_ok=True)

    # Copy this script into the workspace
    src = os.path.abspath(__file__)
    dst = os.path.join(wf_dir, "lambda_cut.py")
    if src != dst:
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
    print(f"  {ok()} Workspace: {workspace}")
    print(f"  {ok()} Script:    {dst}")

    # Update paths to use new workspace
    env_file  = os.path.join(workspace, ".env")
    keys_file = os.path.join(workspace, "gemini_keys.txt")

    print()

    # Dependencies
    print(f"{B}Checking dependencies...{X}")
    missing = False
    for name, cmd in [("python3","python3"),("ffmpeg","ffmpeg"),("ffprobe","ffprobe"),
                       ("yt-dlp","yt-dlp"),("curl","curl")]:
        if shutil.which(cmd):
            try:
                v = subprocess.run([cmd,"--version"], capture_output=True, text=True)
                print(f"  {ok()} {name}  {v.stdout.splitlines()[0]}")
            except Exception:
                print(f"  {ok()} {name}")
        else:
            print(f"  {fail()} {name}  NOT FOUND")
            missing = True

    try:
        import stable_whisper  # noqa: F401
        print(f"  {ok()} stable-ts")
    except ImportError:
        print(f"  {fail()} stable-ts  (pip install stable-ts)")
        missing = True

    if missing:
        print(f"\n  {fail()} Install missing deps first.")
        print("    pip install stable-ts")
        print("    sudo apt install ffmpeg curl python3 yt-dlp")
        sys.exit(1)
    print()

    # Cookies
    print(f"{B}Checking browser cookies...{X}")
    r = subprocess.run(["yt-dlp","--cookies-from-browser","chrome","-j",
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                       capture_output=True)
    if r.returncode == 0:
        print(f"  {ok()} Chrome cookies accessible")
    else:
        print(f"  {warn()} Chrome cookies not accessible.")
        print("    Make sure you're logged into YouTube in Chrome.")
        if input("  Continue? [y/N]: ").strip().lower() != "y":
            sys.exit(1)
    print()

    # Config
    existing = {}
    if os.path.exists(env_file):
        print(f"{warn()} Existing .env found.")
        if input("  Reconfigure? [y/N]: ").strip().lower() == "y":
            with open(env_file) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        existing[k] = v.strip('"')
        else:
            print(f"  {ok()} Keeping existing .env")
            existing = None

    config = {}
    if existing is not None:
        print(f"\n{B}Configuration{X}\n")

        def ask(key, prompt, validate=None, optional=False):
            d = existing.get(key, "")
            hint = f" [{d}]" if d else ""
            while True:
                v = input(f"  {prompt}{hint}: ").strip()
                v = v or d
                if not v and optional:
                    return ""
                if not v:
                    print(f"  {fail()} Required")
                    continue
                if validate and not validate(v):
                    print(f"  {fail()} Invalid format")
                    hint = ""
                    continue
                print(f"  {ok()}")
                return v

        config["GEMINI_API_KEY"] = ask("GEMINI_API_KEY", "Primary Gemini API Key (used for TTS; more keys added below)",
            lambda v: bool(re.match(r"^AIzaSy[A-Za-z0-9_-]{33}$", v)))
        config["PLAYLIST_URL"] = ask("PLAYLIST_URL", "YouTube Playlist URL",
            lambda v: v.startswith("https://www.youtube.com/playlist?list="))

        voices = ["Zephyr","Puck","Charon","Kore","Fenrir","Leda","Orus","Aoede",
                  "Callirhoe","Autonoe","Enceladus","Iapetus","Umbriel","Algieba",
                  "Despina","Erinome","Algenib","Rasalgethi","Schedar","Gacrux",
                  "Pulcherrima","Achird","Zubenelgenubi","Vindemiatrix","Sadachbia",
                  "Sadaltager","Sulafat","Achernar","Alnilam","Laomedeia"]
        default_voice = existing.get("TTS_VOICE", "Vindemiatrix") or "Vindemiatrix"
        default_idx = voices.index(default_voice) + 1 if default_voice in voices else 24
        print(f"\n  TTS Voice (pick a number):")
        for i, v in enumerate(voices, 1):
            marker = f" ({'current' if v == default_voice else 'default'})" if v == default_voice else ""
            print(f"    {i:2d}. {v}{marker}")
        while True:
            choice = input(f"\n  Choice [{default_idx}]: ").strip()
            if not choice:
                config["TTS_VOICE"] = default_voice
                print(f"  {ok()}")
                break
            if choice.isdigit() and 1 <= int(choice) <= len(voices):
                config["TTS_VOICE"] = voices[int(choice) - 1]
                print(f"  {ok()}")
                break
            print(f"  {fail()} Enter a number 1-{len(voices)}")

        config["TTS_STYLE"] = ask("TTS_STYLE", "TTS Style prefix", optional=True) or existing.get("TTS_STYLE","")

        use_telegram = input(f"  Use Telegram notifications? [y/N]: ").strip().lower() == "y"
        if use_telegram:
            print(f"\n  {B}Telegram Bot Token{X}")
            print("    1. Open Telegram, search for @BotFather")
            print("    2. Send /newbot and follow the prompts")
            print("    3. Copy the token (e.g. 123456:ABC-DEF...)")
            config["TELEGRAM_BOT_TOKEN"] = ask("TELEGRAM_BOT_TOKEN", "Telegram Bot Token",
                lambda v: bool(re.match(r"^[0-9]+:[A-Za-z0-9_-]{35}$", v)))

            print(f"\n  {B}Telegram Chat ID{X}")
            print("    1. Open Telegram, search for @userinfobot")
            print("    2. Send /start")
            print("    3. It will reply with your Chat ID")
            config["TELEGRAM_CHAT_ID"] = ask("TELEGRAM_CHAT_ID", "Telegram Chat ID",
                lambda v: bool(re.match(r"^-?[0-9]+$", v)))

        # Keys
        print(f"\n{B}Gemini keys for script generation{X}")
        keys = []
        if os.path.exists(keys_file):
            with open(keys_file) as f:
                keys = [l.strip() for l in f if l.strip()]
        if config["GEMINI_API_KEY"] not in keys:
            keys.insert(0, config["GEMINI_API_KEY"])
        print(f"  Current: {len(keys)}")
        while True:
            sys.stdout.write("  Add key (Enter to skip): "); sys.stdout.flush()
            k = sys.stdin.readline().strip()
            if not k:
                break
            if re.match(r"^AIzaSy[A-Za-z0-9_-]{33}$", k):
                keys.append(k)
                print(f"  {ok()} Added ({len(keys)} total)")
            else:
                print(f"  {fail()} Invalid format")

        # Write
        print(f"\n{B}Writing configuration...{X}")
        if os.path.exists(env_file):
            shutil.copy2(env_file, env_file + ".bak")
        if os.path.exists(keys_file):
            shutil.copy2(keys_file, keys_file + ".bak")

        with open(env_file, "w") as f:
            f.write(f'WORKSPACE={workspace}\n')
            for k in ("GEMINI_API_KEY", "PLAYLIST_URL", "TTS_VOICE"):
                f.write(f'{k}={config[k]}\n')
            if use_telegram:
                for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
                    f.write(f'{k}={config[k]}\n')
            if config["TTS_STYLE"]:
                f.write(f'TTS_STYLE="{config["TTS_STYLE"]}"\n')
        os.chmod(env_file, 0o600)
        print(f"  {ok()} {env_file}")

        with open(keys_file, "w") as f:
            f.write("\n".join(keys) + "\n")
        os.chmod(keys_file, 0o600)
        print(f"  {ok()} {keys_file} ({len(keys)} key(s))")

        print(f"\n{B}Storing keys in system keychain...{X}")
        try:
            set_gemini_keys(keys)
            print(f"  {ok()} Gemini keys stored")
            set_service_password("gemini-api-key", config["GEMINI_API_KEY"])
            print(f"  {ok()} TTS API key stored")
            if use_telegram:
                set_service_password("telegram-bot-token", config["TELEGRAM_BOT_TOKEN"])
                set_service_password("telegram-chat-id", config["TELEGRAM_CHAT_ID"])
                print(f"  {ok()} Telegram keys stored")
        except Exception as e:
            print(f"  {warn()} Keychain not available: {e}")
            print(f"    Keys saved to files only")

    # Reload env
    global ENV, ENV_FILE, KEYS_FILE, WORKSPACE, WORKFLOW_DIR
    ENV_FILE = env_file
    KEYS_FILE = keys_file
    WORKSPACE = workspace
    WORKFLOW_DIR = wf_dir
    ENV = load_env()

    # Verify
    print(f"\n{B}Verifying connections...{X}")
    all_ok = True

    # Gemini
    sys.stdout.write("  Gemini API ... "); sys.stdout.flush()
    try:
        body = json.dumps({"contents":[{"parts":[{"text":"hi"}]}],
                           "generationConfig":{"maxOutputTokens":5}}).encode()
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={env('GEMINI_API_KEY')}",
            data=body, headers={"Content-Type":"application/json"})
        r = urllib.request.urlopen(req, timeout=15)
        json.loads(r.read())
        print(f"{ok()} OK")
    except Exception:
        print(f"{fail()} Failed")
        all_ok = False

    # Telegram
    if _telegram_configured():
        sys.stdout.write("  Telegram bot ... "); sys.stdout.flush()
        try:
            r = urllib.request.urlopen(
                f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/getMe", timeout=10)
            name = json.loads(r.read())["result"]["username"]
            print(f"{ok()} @{name}")
        except Exception:
            print(f"{fail()} Failed")
            all_ok = False

        # Chat
        sys.stdout.write("  Telegram chat ... "); sys.stdout.flush()
        try:
            data = urllib.parse.urlencode({
                "chat_id": env("TELEGRAM_CHAT_ID"),
                "text": "Lambda Cut configured!"
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendMessage",
                data=data, method="POST")
            urllib.request.urlopen(req, timeout=10)
            print(f"{ok()} Message sent")
        except Exception:
            print(f"{fail()} Cannot send to chat")
            all_ok = False
    else:
        print(f"  {warn()} Telegram not configured (notifications disabled)")

    # Playlist
    sys.stdout.write("  YouTube playlist ... "); sys.stdout.flush()
    r = subprocess.run(["yt-dlp","--flat-playlist","--playlist-items","1","-j",
                        env("PLAYLIST_URL")], capture_output=True)
    if r.returncode == 0:
        try:
            title = json.loads(r.stdout).get("title","?")
            print(f"{ok()} \"{title}\"")
        except Exception:
            print(f"{ok()} Accessible")
    else:
        print(f"{fail()} Cannot access")
        all_ok = False

    # Make scripts executable
    for s in ("lambda_cut.py",):
        p = os.path.join(WORKFLOW_DIR, s)
        if os.path.exists(p):
            os.chmod(p, 0o755)

    print()
    if all_ok:
        print(f"{B}{'='*40}")
        print(" All checks passed! You're ready.")
        print(f"{'='*40}{X}\n")

        # Optional: systemd service
        svc_dir  = os.path.expanduser("~/.config/systemd/user")
        svc_file = os.path.join(svc_dir, "lambda-cut-listener.service")
        svc_name = "lambda-cut-listener.service"

        if input(f"  Set up Telegram listener as background service? [y/N]: ").strip().lower() == "y":
            os.makedirs(svc_dir, exist_ok=True)
            python = sys.executable
            svc = f"""[Unit]
Description=Lambda Cut Telegram Listener
After=network.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 10
ExecStart={python} {dst} listen
WorkingDirectory={WORKSPACE}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""
            with open(svc_file, "w") as f:
                f.write(svc)
            run(["systemctl", "--user", "daemon-reload"])
            run(["systemctl", "--user", "enable", svc_name])
            run(["systemctl", "--user", "start", svc_name])
            print(f"  {ok()} Listener running as background service.")
            print(f"    Status:  systemctl --user status {svc_name}")
            print(f"    Stop:    systemctl --user stop {svc_name}")
            print(f"    Disable: systemctl --user disable {svc_name}\n")
        else:
            # Clean up old sophia-listener if present
            old_svc = os.path.join(svc_dir, "sophia-listener.service")
            if os.path.exists(old_svc):
                run(["systemctl", "--user", "stop", "sophia-listener.service"], check=False)
                run(["systemctl", "--user", "disable", "sophia-listener.service"], check=False)
                print(f"  {ok()} Disabled old sophia-listener service.\n")
            print("  Start bot manually when needed:")
            print(f"    python3 {dst} listen\n")

        # Shell alias
        if input("  Set up alias so you can run `lambda_cut` from anywhere? [y/N]: ").strip().lower() == "y":
            alias_line = f"alias lambda_cut='python3 {dst}'"

            # Detect shell rc file
            shell = os.environ.get("SHELL", "")
            rc_candidates = []
            if "zsh" in shell:
                rc_candidates = [os.path.expanduser("~/.zshrc")]
            elif "bash" in shell:
                rc_candidates = [os.path.expanduser("~/.bashrc")]
            else:
                rc_candidates = [os.path.expanduser("~/.bashrc"), os.path.expanduser("~/.zshrc")]

            # Find which rc files exist
            existing_rcs = [rc for rc in rc_candidates if os.path.exists(rc)]
            if not existing_rcs:
                # Create the first candidate
                rc_file = rc_candidates[0]
            elif len(existing_rcs) == 1:
                rc_file = existing_rcs[0]
            else:
                print(f"    Multiple shell configs found:")
                for i, rc in enumerate(existing_rcs, 1):
                    print(f"      {i}. {rc}")
                choice = input("    Which one? [1]: ").strip()
                idx = int(choice) - 1 if choice.isdigit() and 0 < int(choice) <= len(existing_rcs) else 0
                rc_file = existing_rcs[idx]

            # Check if alias already exists
            alias_exists = False
            if os.path.exists(rc_file):
                with open(rc_file) as f:
                    for line in f:
                        if line.strip().startswith("alias lambda_cut="):
                            alias_exists = True
                            break

            if alias_exists:
                print(f"  {warn()} Alias already exists in {rc_file}")
            else:
                with open(rc_file, "a") as f:
                    f.write(f"\n# Lambda Cut\n{alias_line}\n")
                print(f"  {ok()} Alias added to {rc_file}")
                print(f"    Run: source {rc_file}")
                print(f"    Or open a new terminal.\n")

            print(f"  {B}Ready!{X}")
            print(f"    lambda_cut run")
            print(f"    lambda_cut run -phase 2,3")
            print(f"    lambda_cut listen\n")
        else:
            print(f"  {B}Ready!{X}")
            print(f"    python3 {dst} run")
            print(f"    python3 {dst} run -phase 2,3")
            print(f"    python3 {dst} listen\n")

    else:
        print(f"{B}{'='*40}")
        print(" Some checks failed. Fix and re-run.")
        print(f"{'='*40}{X}\n")

# ─── Config check ─────────────────────────────────────────────────────────────
REQUIRED_KEYS = ("GEMINI_API_KEY", "PLAYLIST_URL")

def _check_configured():
    """Return True if .env exists and all required keys have real values."""
    if not os.path.exists(ENV_FILE):
        return False
    for key in REQUIRED_KEYS:
        val = env(key)
        if not val:
            return False
    return True

def _telegram_configured():
    return bool(env("TELEGRAM_BOT_TOKEN")) and bool(env("TELEGRAM_CHAT_ID"))

# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(prog="lambda_cut", description="Lambda Cut — YouTube Shorts Pipeline")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run the pipeline")
    p_run.add_argument("-phase", type=str, help="Run only phases (e.g. 2,3)")
    p_run.add_argument("-index", type=int, help="Playlist index to download (default: 1)")
    p_run.add_argument("-skip-phase-1", action="store_true")
    p_run.add_argument("-skip-phase-2", action="store_true")
    p_run.add_argument("-skip-phase-3", action="store_true")
    p_run.add_argument("-skip-phase-4", action="store_true")
    p_run.add_argument("-skip-phase-5", action="store_true")
    p_run.add_argument("-skip-all", action="store_true")

    sub.add_parser("listen", help="Start Telegram bot listener")
    
    p_stop = sub.add_parser("stop", help="Stop the listener")
    p_stop.add_argument("--pipeline", action="store_true", help="Stop the running pipeline instead")

    sub.add_parser("delete-partial", help="Delete incomplete files")
    sub.add_parser("cleanup", help="Delete all generated files")
    sub.add_parser("clear-logs", help="Clear pipeline logs")
    sub.add_parser("onboard", help="Interactive setup wizard")

    args = parser.parse_args()

    if args.command == "run":
        if not _check_configured():
            print("Configuration missing or incomplete.")
            print(f"  .env: {ENV_FILE}")
            print(f"  Run onboarding first:  python3 {__file__} onboard")
            sys.exit(1)

        skip = set()
        if args.skip_all:
            skip = {1,2,3,4,5}
        else:
            if args.skip_phase_1: skip.add(1)
            if args.skip_phase_2: skip.add(2)
            if args.skip_phase_3: skip.add(3)
            if args.skip_phase_4: skip.add(4)
            if args.skip_phase_5: skip.add(5)

        phases = None
        if args.phase:
            phases = [int(p) for p in args.phase.split(",")]

        playlist_index = None
        if args.index:
            playlist_index = str(args.index)
            update_env_var("PLAYLIST_INDEX", playlist_index)

        run_pipeline(skip=skip, phases=phases)

    elif args.command == "listen":
        listen()

    elif args.command == "stop":
        if args.pipeline:
            if PIPELINE_RUNNING:
                global PIPELINE_STOP_REQUESTED
                PIPELINE_STOP_REQUESTED = True
                print("Stop requested for pipeline.")
            else:
                print("No pipeline is currently running.")
        else:
            if os.path.exists(PID_FILE):
                with open(PID_FILE) as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)
                    os.kill(pid, 15)
                    print(f"Sent stop signal to listener (PID {pid})")
                    os.remove(PID_FILE)
                except ProcessLookupError:
                    print("Listener not running.")
                    os.remove(PID_FILE)
                except PermissionError:
                    print("Cannot stop listener (permission denied).")
            else:
                print("No listener running (PID file not found).")

    elif args.command == "delete-partial":
        count = delete_partial_files()
        print(f"Deleted {count} partial file(s).")

    elif args.command == "cleanup":
        count = cleanup_all_files()
        print(f"Deleted {count} file(s) from all output directories.")

    elif args.command == "clear-logs":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                f.write("")
            print("Pipeline logs cleared.")
        else:
            print("No logs to clear.")

    elif args.command == "onboard":
        onboard()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
