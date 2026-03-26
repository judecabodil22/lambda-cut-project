#!/usr/bin/env python3
"""
Lambda Cut — YouTube Shorts Pipeline
Combines: lambda_cut.sh, telegram_listener.sh, generate_script.sh, onboard.sh
"""
import argparse, base64, glob, html, json, os, re, shutil, subprocess, sys, threading, time, urllib.error, urllib.request

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

STREAMING = False  # set True when called from listener
PIPELINE_RUNNING = False

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
def tg_send(msg):
    token = env("TELEGRAM_BOT_TOKEN")
    chat  = env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": msg, "parse_mode": "HTML"}).encode()
        req  = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                      data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log_error(f"Telegram: {e}")

def notify(msg):
    if not STREAMING:
        tg_send(msg)

# ─── Helpers ──────────────────────────────────────────────────────────────────
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

def run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

# ─── Phase 1: Download ────────────────────────────────────────────────────────
def phase_download():
    set_status("Phase 1: Downloading video...")
    log("Phase 1: Downloading 1440p stream...")
    notify("Phase 1 Started: Downloading video...")

    def do_dl():
        r = run(["yt-dlp", "--playlist-items", "1",
                 "--cookies-from-browser", "chrome",
                 "-f", "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                 "-o", f"{STREAMS_DIR}/%(title)s.%(ext)s",
                 env("PLAYLIST_URL")])
        log(r.stdout[-500:] if r.stdout else "")

    if not retry(do_dl, 3, 10, "Download video"):
        log_error("Phase 1 failed after 3 attempts")
        notify("Phase 1 Failed: Download failed after 3 attempts")
        set_status("Phase 1 FAILED")
        raise RuntimeError("Phase 1 failed")

    set_status("Phase 1 Complete")
    notify("Phase 1 Complete: Video downloaded")

# ─── Phase 2: Transcribe ──────────────────────────────────────────────────────
def phase_transcribe(video):
    basename = os.path.splitext(os.path.basename(video))[0]
    json_file = os.path.join(TRANSCRIPTS_DIR, f"{basename}.json")

    if os.path.exists(json_file):
        log("Phase 2: Transcript exists, skipping")
        notify("Phase 2 Skipped (transcript exists)")
        return json_file

    set_status("Phase 2: Transcribing...")
    log("Phase 2: Transcribing via stable-ts...")
    try:
        import stable_whisper
        model = stable_whisper.load_model("base")
        result = model.transcribe(video, language="en", vad=True)
        result.to_srt(os.path.join(TRANSCRIPTS_DIR, f"{basename}.srt"))
        result.to_json(os.path.join(TRANSCRIPTS_DIR, f"{basename}.json"))
    except ImportError:
        run(["stable-ts", "-y", video, "--output_dir", TRANSCRIPTS_DIR,
             "--output_format", "srt,json", "--word_timestamps", "False",
             "--vad", "True", "--language", "en"])

    if not os.path.exists(json_file):
        log_error("Phase 2: transcript file not created")
        raise RuntimeError("Transcription failed")

    notify("Phase 2 Complete: Transcript generated")
    set_status("Phase 2 Complete")
    return json_file

# ─── Phase 3: Scripts ─────────────────────────────────────────────────────────
SCRIPT_PROMPT = """Generate a script for YouTube Shorts narrating the events from the protagonist's POV, blending first-person narration with direct quotes from the transcript. Format the script as follows:

Title: "Script {num}: [Create a fitting title]"

The title must use the exact script number provided ({num}). Script body should be continuous prose, not bullet points. Include 2-3 direct quotes from the transcript in italics. The narration should be in first person. End with a cliffhanger.

Example:
Title: Script 2: The Widow's Enterprise

I'm standing before the spirit of Lucy, a woman who hasn't realized her tavern days are long over.
My husband and I ran a tavern in England.

IMPORTANT: The script must be under 150 words.

Now generate a script based ONLY on this scene dialogue:
{transcript}"""

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
    with open(keys_file) as f:
        keys = [l.strip() for l in f if l.strip()]
    if not keys:
        raise RuntimeError("No API keys in gemini_keys.txt")

    prompt = SCRIPT_PROMPT.format(num=script_num, transcript=text[:3000])
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 512}
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
            if t and len(t.split()) >= 10:
                parts.append(t)
    return "\n".join(parts)

def phase_scripts(json_file, duration, num_hours):
    set_status("Phase 3: Generating scripts...")
    log("Phase 3: Generating scripts (one per hour)...")
    notify(f"Phase 3 Started: Generating {num_hours} scripts...")
    delay = int(env("SCRIPT_DELAY", "300"))

    for i in range(1, num_hours + 1):
        padded = f"{i:03d}"
        h_start = (i - 1) * 3600
        h_end   = min(i * 3600, duration)
        out     = os.path.join(SCRIPTS_DIR, f"script_{padded}.txt")

        if os.path.exists(out):
            log(f"   Skipping script {i} (exists)")
            continue

        log(f"   Processing hour {i}: {h_start}s - {h_end}s")
        text = _extract_hour(json_file, h_start, h_end)
        if not text:
            log(f"   No transcript for hour {i}, skipping")
            continue

        script = _gemini_script(text[:3000], i, KEYS_FILE)
        if script is None:
            log(f"   All keys failed for hour {i}, using raw transcript")
            script = text[:3000]

        with open(out, "w") as f:
            f.write(script)
        wc = len(script.split())
        log(f"   Script {i}: {wc} words")
        set_status(f"Phase 3: Script {i}/{num_hours} generated")
        notify(f"Script {i}/{num_hours} generated ({wc} words)")
        if i < num_hours:
            log(f"   Waiting {delay}s")
            time.sleep(delay)

    set_status("Phase 3 Complete")
    notify(f"Phase 3 Complete: {num_hours} scripts generated")

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
    return scenes[:5]

def phase_clips(video, json_file, duration, num_hours):
    set_status("Phase 4: Generating clips...")
    log("Phase 4: Generating clips (scene-based)...")
    notify("Phase 4 Started: Generating clips...")
    vaapi = os.path.exists("/dev/dri/renderD128")

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
            if os.path.exists(out):
                log(f"   Skipping {name} (exists)")
                continue

            s, e = int(sc["start"]), int(sc["end"])
            dur  = e - s
            log(f"   Hour {i}, scene {idx}: {s}s-{e}s ({dur}s)")

            if vaapi:
                cmd = ["ffmpeg", "-y", "-vaapi_device", "/dev/dri/renderD128",
                       "-ss", str(s), "-i", video, "-t", str(dur),
                       "-filter_complex", "[0:a]loudnorm[aout]",
                       "-vf", "format=nv12,hwupload",
                       "-c:v", "h264_vaapi", "-qp", "18",
                       "-c:a", "aac", "-b:a", "192k",
                       "-map", "0:v", "-map", "[aout]", out]
                enc = "VAAPI"
            else:
                cmd = ["ffmpeg", "-y", "-ss", str(s), "-i", video, "-t", str(dur),
                       "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                       "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", out]
                enc = "CPU"

            r = run(cmd, check=False)
            if r.returncode == 0:
                log(f"   {name} created ({enc})")
            else:
                log_error(f"Failed {name}: {r.stderr[-200:]}")

    set_status("Phase 4 Complete")
    notify("Phase 4 Complete: Clips generated")

# ─── Phase 5: TTS ─────────────────────────────────────────────────────────────
def _tts_api(text, out_pcm, voice, style):
    if style:
        text = f"{style} {text}"
    body = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}
        }
    }).encode()
    key = env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = json.loads(resp.read())
        audio = r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        with open(out_pcm, "wb") as f:
            f.write(base64.b64decode(audio))

def phase_tts(duration, num_hours):
    set_status("Phase 5: Generating TTS...")
    log("Phase 5: Generating TTS...")
    notify("Phase 5 Started: Generating TTS...")
    voice = env("TTS_VOICE", "Algenib")
    style = env("TTS_STYLE", "")
    delay = int(env("TTS_DELAY", "300"))

    for i in range(1, num_hours + 1):
        padded = f"{i:03d}"
        wav = os.path.join(TTS_DIR, f"tts_{padded}.wav")
        srt = os.path.join(TTS_DIR, f"tts_{padded}.srt")
        script_file = os.path.join(SCRIPTS_DIR, f"script_{padded}.txt")

        if not os.path.exists(wav):
            if not os.path.exists(script_file):
                log(f"   Script {i} not found, skipping TTS")
                continue
            log(f"   Generating TTS for script {i}...")
            with open(script_file) as f:
                txt = f.read()

            pcm = os.path.join(TTS_DIR, f"tts_{padded}.pcm")
            try:
                _tts_api(txt, pcm, voice, style)
            except Exception as e:
                log_error(f"TTS failed for script {i}: {e}")
                continue

            if not os.path.exists(pcm):
                log_error(f"TTS failed for script {i}")
                continue

            run(["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1",
                 "-i", pcm, "-ar", "44100", "-ac", "2", wav])
            os.remove(pcm)
            log(f"   tts_{padded}.wav created")
            set_status(f"Phase 5: TTS {i}/{num_hours} generated")
            notify(f"TTS {i}/{num_hours} generated")
        else:
            log(f"   TTS {i} WAV exists, skipping")

        if not os.path.exists(srt):
            log(f"   Generating SRT for tts_{padded}.wav...")
            try:
                import stable_whisper
                model = stable_whisper.load_model("base")
                result = model.transcribe(wav, language="en")
                result.to_srt(srt)
            except ImportError:
                run(["stable-ts", wav, "--device", "cpu",
                     "--word_timestamps", "False", "--language", "en",
                     "-o", srt], check=False)
            log(f"   tts_{padded}.srt created" if os.path.exists(srt) else
                log_error(f"   SRT failed for tts_{padded}"))
        else:
            log(f"   tts_{padded}.srt exists, skipping")

        if i < num_hours:
            log(f"   Waiting {delay}s")
            time.sleep(delay)

    set_status("Phase 5 Complete")
    notify("Phase 5 Complete: TTS generation done")

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

# ─── Pipeline orchestrator ────────────────────────────────────────────────────
def run_pipeline(skip=None, phases=None):
    for d in (STREAMS_DIR, TRANSCRIPTS_DIR, SCRIPTS_DIR, TTS_DIR, SHORTS_DIR):
        os.makedirs(d, exist_ok=True)

    skip = skip or set()
    if phases:
        skip = {1,2,3,4,5} - set(phases)

    if 1 not in skip:
        phase_download()

    video = find_video()
    if not video:
        log_error("No video found in streams/")
        return
    duration = video_info(video)
    log(f"Target: {os.path.basename(video)} ({duration}s)")

    json_file = phase_transcribe(video) if 2 not in skip else \
        (sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.json")),
                key=os.path.getmtime, reverse=True)[0]
         if glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.json")) else None)

    num_hours = max(1, duration // 3600)
    log(f"Video: {duration}s = {num_hours} hour(s)")

    if 3 not in skip and json_file:
        phase_scripts(json_file, duration, num_hours)
    elif 3 not in skip:
        log_error("No transcript for script generation")

    if 4 not in skip and json_file:
        phase_clips(video, json_file, duration, num_hours)
    elif 4 not in skip:
        log_error("No transcript for clip generation")

    if 5 not in skip:
        phase_tts(duration, num_hours)

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
            tg_send("Pipeline triggered!")
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
            tg_send("Usage: /set_voice Algenib\nVoices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat, Achernar, Alnilam, Laomedeia")
        else:
            update_env_var("TTS_VOICE", args)
            tg_send(f"Voice set to: {args}")

    elif cmd in ("/set_style", "/setstyle"):
        if not args:
            update_env_var("TTS_STYLE", "")
            tg_send("Style cleared.")
        else:
            update_env_var("TTS_STYLE", args)
            tg_send(f"Style set to: {args}")

    elif cmd in ("/config", "/settings"):
        voice = env("TTS_VOICE", "Algenib")
        style = env("TTS_STYLE") or "(none)"
        status = "Running" if PIPELINE_RUNNING else "Idle"

        wc = count_files(os.path.join(WORKSPACE, "tts/*.wav"))
        sc = count_files(os.path.join(WORKSPACE, "tts/*.srt"))
        rc = count_files(os.path.join(WORKSPACE, "scripts/*.txt"))
        cc = count_files(os.path.join(WORKSPACE, "shorts/*.mp4"))
        tg_send(f"Config:\nVoice: {voice}\nStyle: {style}\nStatus: {status}\n\nFiles:\nScripts: {rc}\nClips: {cc}\nTTS WAVs: {wc}\nTTS SRTs: {sc}")

    elif cmd == "/status":
        s = open(STATUS_FILE).read() if os.path.exists(STATUS_FILE) else ""
        if PIPELINE_RUNNING:
            tg_send(f"Running: {s}" if s else "Running")
        else:
            tg_send(f"Idle. Last: {s}" if s else "Idle")

    elif cmd == "/logs":
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                lines = f.readlines()[-20:]
            txt = html.escape("".join(lines))[:1500]
            tg_send(f"Last 20 lines:\n{txt}")
        else:
            tg_send("No logs found.")

    elif cmd == "/help":
        tg_send("""Available Commands

/run_pipeline - Run full pipeline
/run_phase 5 - Run phase 5 only
/run_phase 2,3 - Run phases 2 and 3
/skip_phase 1,2 - Skip phases 1 and 2

Phases  1 Download  2 Transcribe  3 Scripts  4 Clips  5 TTS

/set_voice Puck - Change TTS voice
/set_style Say in a Scottish accent - Set style prefix
/set_style - Clear style

/config - Show settings and file counts
/status - Pipeline running or idle
/logs - Last 20 log lines
/help - This message""")

    else:
        tg_send("Unknown command. Use /help for available commands.")

def listen():
    if not _telegram_configured():
        print("Telegram not configured. Run onboard and enable Telegram to use the listener.")
        sys.exit(1)

    token = env("TELEGRAM_BOT_TOKEN")
    chat  = env("TELEGRAM_CHAT_ID")

    global STREAMING
    STREAMING = True

    me = tg_api("getMe")
    print(f"Lambda Cut Listener — @{me['result']['username']}")
    tg_send("Lambda Cut listener started.")
    offset = 0

    while True:
        try:
            r = tg_api("getUpdates", {"limit": 3, "timeout": 30, "offset": offset})
            if not r.get("ok"):
                time.sleep(5)
                continue
            for upd in r["result"]:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                cid = str(msg.get("chat", {}).get("id", ""))
                txt = msg.get("text", "")
                if cid == str(chat) and txt:
                    print(f"Received: {txt}")
                    process_cmd(txt, cid)
        except urllib.error.URLError:
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

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
        import stable_whisper
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
                  "Callirrhoe","Autonoe","Enceladus","Iapetus","Umbriel","Algieba",
                  "Despina","Erinome","Algenib","Rasalgethi","Schedar","Gacrux",
                  "Pulcherrima","Achird","Zubenelgenubi","Vindemiatrix","Sadachbia",
                  "Sadaltager","Sulafat","Achernar","Alnilam","Laomedeia"]
        default_voice = existing.get("TTS_VOICE", "Algenib") or "Algenib"
        default_idx = voices.index(default_voice) + 1 if default_voice in voices else 17
        print(f"\n  TTS Voice (pick a number):")
        for i, v in enumerate(voices, 1):
            marker = f" ({'current' if v == default_voice else 'default'})" if v == default_voice or (v == 'Algenib' and default_voice == 'Algenib') else ""
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
                "text": "Lambda Cut configured!",
                "parse_mode": "HTML"
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
ExecStart={python} {dst} listen
WorkingDirectory={WORKSPACE}
Restart=on-failure
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
    p_run.add_argument("-skip-phase-1", action="store_true")
    p_run.add_argument("-skip-phase-2", action="store_true")
    p_run.add_argument("-skip-phase-3", action="store_true")
    p_run.add_argument("-skip-phase-4", action="store_true")
    p_run.add_argument("-skip-phase-5", action="store_true")
    p_run.add_argument("-skip-all", action="store_true")

    sub.add_parser("listen", help="Start Telegram bot listener")
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

        run_pipeline(skip=skip, phases=phases)

    elif args.command == "listen":
        listen()

    elif args.command == "onboard":
        onboard()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
