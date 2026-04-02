# Content Studio - Plan Document

## Feature Overview

**Feature Name:** Content Studio  
**Type:** Standalone content generation tool (not part of main pipeline)  
**Access:** Via Telegram commands  
**Purpose:** Generate additional content (analysis, opinions, theories, speculation) from existing transcripts and clips

---

## 1. Core Functionality

### 1.1 Auto-Detect System

The feature will analyze input transcripts and automatically determine:

| Detection | Description |
|-----------|-------------|
| **Subject Detection** | Identifies the subject (character name, game title, episode, theme) from transcript content |
| **Content Type Selection** | Based on subject analysis, selects the most appropriate content type |

**Flow:**
```
Transcript Input → AI Analysis → Auto-detect Subject → Auto-select Content Type
                                    ↓
                            Notify user: "Generating [Content Type] about [Subject]"
```

### 1.2 Content Types (Variants)

| # | Content Type | Description | Voice Style Match |
|---|--------------|-------------|-------------------|
| 1 | **Speculation & Theories** | "What If" scenarios, plot theories, future predictions | Mysterious/Intriguing |
| 2 | **Choice Consequences** | Analysis of player decisions and outcomes | Thoughtful/Reflective |
| 3 | **Mystery Reveals** | Hidden details, plot twists, missed details | Investigative/True Crime |
| 4 | **Character Analysis** | Deep dive into character motivations, arcs, psychology | Documentary/Educational |
| 5 | **Opinion & Review** | Episode reviews, hot takes, rankings | Conversational/Friendly |
| 6 | **Lore & World Building** | Game world details, backstory, history | Educational/Informative |

### 1.3 Subject Detection Logic

AI analyzes transcript to identify:

| Subject Type | Detection Method |
|--------------|------------------|
| **Character** | Most frequently mentioned character name |
| **Game** | Game title mentions in transcript |
| **Episode** | Episode number/segment identification |
| **Theme** | Core theme detection (time travel, loss, friendship, etc.) |

---

## 2. Telegram Interface

### 2.1 Command Structure

**Primary Command:**
```
/content_studio
```

**Response:** Shows interactive menu with options

**Simplified Commands:**
```
/theory     → Auto-generate speculation content
/analyze    → Auto-generate character analysis
/review     → Auto-generate opinion/review content
/mystery    → Auto-generate mystery reveals content
/lore       → Auto-generate lore content
```

### 2.2 User Flow

1. User sends command (e.g., `/theory`)
2. System scans available transcripts
3. AI analyzes transcript → detects subject + content type
4. System notifies user: "Generating Speculation about Nathan Prescott"
5. AI generates script (auto-detected content type)
6. TTS generated (matching voice style to content type)
7. Output saved to Content Studio folder

---

## 3. Script & TTS Generation

### 3.1 Target Duration: 10 Minutes

| Parameter | Value |
|-----------|-------|
| Target Duration | 10 minutes |
| Target Word Count | ~1,500 words |
| TTS Segments Needed | 2 segments (750 words each) |
| API Calls | 2 sequential calls |

### 3.2 Concatenation Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Same Voice** | Use same voice for all segments (rotated per session) |
| **Same Style** | Use same TTS style instruction throughout |
| **Smooth Transition** | Use ffmpeg to concatenate without audio gaps |

### 3.3 Voice Style Matching

Each content type maps to a specific TTS style:

| Content Type | TTS Style Instruction |
|--------------|----------------------|
| Speculation | "Speak with intrigue and mystery. Hint at secrets without revealing." |
| Choice Consequences | "Speak thoughtfully and reflectively. Like weighing options carefully." |
| Mystery Reveals | "Speak with investigative intensity. Build suspense naturally." |
| Character Analysis | "Speak like a documentary host. Informed, educational, objective." |
| Opinion & Review | "Speak naturally like telling a friend. Conversational, honest." |
| Lore & World Building | "Speak like a knowledgeable guide. Educational and warm." |

---

## 4. Technical Implementation

### 4.1 Directory Structure

```
lambda_cut/
├── content_studio/
│   ├── scripts/          # Generated scripts
│   ├── tts/             # Generated TTS audio
│   └── output/          # Final concatenated audio
├── transcripts/         # (existing)
└── clips/                # (existing - reused)
```

### 4.2 Script Generation Logic

```python
def generate_content(transcript_path, command_type):
    # Step 1: Analyze transcript
    subject = detect_subject(transcript_path)
    content_type = select_content_type(subject, command_type)
    
    # Step 2: Notify user
    notify_user(f"Generating {content_type} about {subject}")
    
    # Step 3: Generate script (~1500 words)
    script = generate_script(subject, content_type)
    
    # Step 4: Generate TTS (2 segments)
    audio_segment_1 = tts_generate(script[:750], voice, style)
    audio_segment_2 = tts_generate(script[750:], voice, style)
    
    # Step 5: Concatenate
    final_audio = concatenate(audio_segment_1, audio_segment_2)
    
    return final_audio
```

### 4.3 Round-Robin Reuse

Use existing pipeline logic:

| Component | Source |
|-----------|--------|
| Voice rotation | Reuse pipeline's voice selection |
| API key rotation | Reuse pipeline's multi-key system |
| TTS rate limiting | Reuse pipeline's delay logic |

### 4.4 Script Template

Each content type has a prompt template:

```
CONTENT_TYPE: {selected_type}
SUBJECT: {detected_subject}

Generate a 1500-word script that:
- Focuses on the detected subject
- Uses the appropriate content style
- Is engaging and suitable for 10-minute audio
- Has natural paragraph flow (NOT poetic fragments)
- Includes hook at start and CTA at end
```

---

## 5. Feature Isolation

### 5.1 Separate from Pipeline

| Aspect | Content Studio | Main Pipeline |
|--------|---------------|---------------|
| Location | `content_studio/` folder | `workflows/lambda_cut.py` |
| Commands | `/content_studio`, `/theory`, etc. | `/run_pipeline`, `/run_phase` |
| Triggers | Manual command | YouTube/Local trigger |
| Output | New content | Video production |

### 5.2 Independent Function

- Does not modify any existing pipeline code
- Uses existing transcripts and clips as input
- Creates separate output directory
- Can run while pipeline is active

---

## 6. Notifications & User Feedback

### 6.1 Auto-Notify Messages

On generation start:
```
🔄 Creating Content Studio content...
📋 Detected: Character Analysis
👤 Subject: Nathan Prescott
⏱️ Target: 10 minutes
```

On completion:
```
✅ Content Generated!
📝 Type: Character Analysis
👤 Subject: Nathan Prescott
📁 Saved: content_studio/tts/
```

### 6.2 Error Handling

| Error | Response |
|-------|-----------|
| No transcripts found | "No transcripts available. Run Phase 2 first." |
| TTS rate limit | Retry with next key, notify if all fail |
| Script generation fails | "Content generation failed. Try again." |

---

## 7. Implementation Priority

### Phase 1: Core Features
1. Auto-detect subject (character, game, episode)
2. Auto-select content type based on subject
3. 10-minute script generation
4. TTS with voice/style matching
5. Audio concatenation

### Phase 2: Enhancements (Future)
1. Multiple content type selection
2. Custom subject input
3. Batch generation
4. Thumbnail generation

---

## 8. Summary

| Component | Status |
|-----------|--------|
| Auto-detect subject | To be implemented |
| Auto-detect content type | To be implemented |
| 10-minute target | To be implemented |
| Voice/style matching | To be implemented |
| Separate from pipeline | Confirmed |
| Telegram commands | To be implemented |

---

## Questions for Review

1. Is this plan comprehensive enough?
2. Are the content types appropriate?
3. Should I proceed with implementation?
4. Any modifications needed before implementation?

---

**Document Version:** 1.0  
**Created:** 2026-04-02  
**Status:** Pending Review