# URGENT: Telegram Inline Menu - Implementation Plan

**Created:** 2026-04-02  
**Priority:** HIGH  
**Status:** READY FOR IMPLEMENTATION

---

## Overview

Add interactive inline keyboard menus to the Telegram bot for easier user interaction without typing commands.

---

## Current State

- 27 text-based commands
- User must remember exact command syntax
- No visual feedback on available options

---

## Target State

- Inline keyboard buttons for common actions
- One-tap execution
- Visual menu navigation
- Better user experience

---

## Implementation Components

### 1. Main Menu Layout

```
┌─────────────────────────────────────┐
│  📊 Status   │  ▶️ Run Pipeline     │
├─────────────────────────────────────┤
│  📝 Scripts  │  🎬 Clips            │
├─────────────────────────────────────┤
│  🎤 TTS       │  🔄 Restart Listener │
├─────────────────────────────────────┤
│  ⚙️ Config   │  📋 Help             │
├─────────────────────────────────────┤
│  🔍 Update   │  🛑 Stop             │
└─────────────────────────────────────┘
```

### 2. Callback Handlers

| Button | Action | Description |
|--------|--------|-------------|
| 📊 Status | `/status` | Show listener and pipeline status |
| ▶️ Run Pipeline | `/run_pipeline` | Run full pipeline |
| 📝 Scripts | Phase 3 only | Generate scripts |
| 🎬 Clips | Phase 4 only | Extract clips |
| 🎤 TTS | Phase 5 only | Generate TTS |
| 🔄 Restart Listener | `/restart_listener` | Restart listener |
| ⚙️ Config | `/config` | Show settings |
| 📋 Help | `/help` | Show help |
| 🔍 Update | `/update` | Check for updates |
| 🛑 Stop | `/stop_pipeline` | Stop running pipeline |

### 3. Additional Menus

**Run Menu (from /run):**
```
┌─────────────────────────────────────┐
│  📥 Full Pipeline │  📥 Download   │
├─────────────────────────────────────┤
│  📝 Scripts      │  🎬 Clips      │
├─────────────────────────────────────┤
│  🎤 TTS          │  ⬅️ Back       │
└─────────────────────────────────────┘
```

**Config Menu:**
```
┌─────────────────────────────────────┐
│  🎤 Voice    │  📝 Index          │
├─────────────────────────────────────┤
│  🎵 Style    │  🎮 Game          │
├─────────────────────────────────────┤
│  📁 Source   │  ⬅️ Back          │
└─────────────────────────────────────┘
```

---

## Technical Implementation

### Files to Modify
1. `workflows/lambda_cut.py` - Add callback handlers and menu generator

### New Functions Required
1. `get_main_menu()` - Returns InlineKeyboardMarkup
2. `get_run_menu()` - Returns run options menu
3. `get_config_menu()` - Returns config options menu
4. `handle_callback(update)` - Process callback queries
5. `/menu` command - Show main menu

### Integration Points
1. Add callback query handler in listener loop
2. Add `/menu` command
3. Modify message handlers to support callback responses

---

## Implementation Steps

### Step 1: Add Menu Generator Functions
- Create keyboard layout functions
- Define button structures
- Set callback data patterns

### Step 2: Add Callback Handler
- Parse callback data
- Route to appropriate function
- Handle errors gracefully

### Step 3: Add /menu Command
- Show main menu on command
- Include help text

### Step 4: Test and Refine
- Test all buttons
- Verify callback responses
- Fix any issues

---

## Success Criteria

- [ ] Main menu displays with all 10 buttons
- [ ] Each button triggers correct action
- [ ] Callback query answered (shows "loading" or "done")
- [ ] Navigation works (Back buttons)
- [ ] No errors on button clicks
- [ ] Works alongside existing commands

---

## User Experience Improvement

| Before | After |
|--------|-------|
| Type `/status` | Tap 📊 Status |
| Type `/run_pipeline` | Tap ▶️ Run Pipeline |
| Type `/restart_listener` | Tap 🔄 Restart |
| Remember commands | See buttons |

---

## Notes

- All existing commands still work
- Menu is optional (can still use text commands)
- Callback queries provide feedback
- Menu state maintained in conversation

---

**Implementation Ready: YES**  
**Start After: User Approval**