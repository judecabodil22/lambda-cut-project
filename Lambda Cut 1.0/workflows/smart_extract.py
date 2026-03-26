import json, re, sys

file = sys.argv[1]
hour_start = int(sys.argv[2])
hour_end = int(sys.argv[3])

with open(file) as f:
    data = json.load(f)

def clean(text):
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def time_to_seconds(t):
    parts = t.replace(',', '.').split(':')
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

# Scene detection: group consecutive entries where gaps < threshold
SCENE_GAP = 15  # seconds - entries closer than this belong to the same scene
MIN_SCENE_WORDS = 15  # minimum words in a scene to be considered
MIN_SCENE_DURATION = 30  # minimum seconds for a scene
MAX_SCENE_DURATION = 600  # maximum 10 minutes per scene
PADDING = 5  # seconds to add before/after scene

# Collect all entries in the hour window
entries = []
for seg in data["segments"]:
    if seg["start"] < hour_start or seg["end"] > hour_end:
        continue
    text = clean(seg["text"])
    words = len(text.split())
    if words < 3:
        continue
    entries.append({
        "start": seg["start"],
        "end": seg["end"],
        "text": text,
        "words": words
    })

if not entries:
    print("NONE")
    sys.exit(0)

entries.sort(key=lambda x: x["start"])

# Group entries into scenes based on time gaps
scenes = []
current_scene = [entries[0]]

for i in range(1, len(entries)):
    gap = entries[i]["start"] - entries[i - 1]["end"]
    scene_duration = entries[i]["end"] - current_scene[0]["start"]

    if gap <= SCENE_GAP and scene_duration <= MAX_SCENE_DURATION:
        current_scene.append(entries[i])
    else:
        scenes.append(current_scene)
        current_scene = [entries[i]]

scenes.append(current_scene)

# Score and filter scenes
scored_scenes = []
for scene in scenes:
    total_words = sum(e["words"] for e in scene)
    duration = scene[-1]["end"] - scene[0]["start"]
    num_entries = len(scene)

    if total_words < MIN_SCENE_WORDS or duration < MIN_SCENE_DURATION:
        continue

    # Score: prefer longer scenes with more dialogue
    # Bonus for scenes with questions/exclamations (dramatic moments)
    dialogue_density = total_words / max(duration, 1)
    text_combined = " ".join(e["text"] for e in scene)
    drama_bonus = text_combined.count('?') * 2 + text_combined.count('!') * 2

    score = total_words + dialogue_density * 10 + drama_bonus

    scored_scenes.append({
        "start": max(scene[0]["start"] - PADDING, hour_start),
        "end": min(scene[-1]["end"] + PADDING, hour_end),
        "words": total_words,
        "duration": duration,
        "entries": num_entries,
        "score": score,
        "text": text_combined[:200]
    })

if not scored_scenes:
    print("NONE")
    sys.exit(0)

# Sort by score, return best scenes
scored_scenes.sort(key=lambda x: x["score"], reverse=True)

# Output: top scenes (one per line for the caller to process)
for scene in scored_scenes[:5]:
    print(f"{int(scene['start'])}|{int(scene['end'])}|{scene['text']}")
