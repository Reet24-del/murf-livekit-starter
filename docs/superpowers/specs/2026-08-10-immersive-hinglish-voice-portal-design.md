# Immersive Hinglish Voice Portal Design

Date: 2026-08-10
Status: Approved design

## Goal

Transform Kisan Sahayak from a narrow, mobile-style voice screen into a polished, responsive website-format voice experience. The agent must mirror the language style of every user turn: English, Devanagari Hindi, or Roman-script Hinglish.

## Selected Direction

The selected visual direction is **Futuristic AI**, using the **Immersive Voice Portal** layout chosen in the visual companion.

The site will use a near-black navy background, emerald primary energy, violet AI light, and limited amber warning accents. A large animated voice orb is the dominant visual element. Supporting information appears as lightweight floating panels instead of a dense dashboard.

## Website Structure

### Top navigation

- Kisan Sahayak identity on the left.
- Connection status and a compact memory-reset control on the right.
- Language support is described as automatic; the design does not require the user to choose a response language manually.

### Main voice stage

- A large animated AI orb is centered in the primary viewport.
- The orb visually distinguishes Ready, Connecting, Listening, Thinking, Speaking, Ended, and Microphone Blocked states.
- A single prominent Start Call or End Call action sits below the orb.
- The Ready state shows a short bilingual instruction. After the user speaks, state text and responses follow the latest detected language mode.

### Supporting panels

- A live weather panel floats to the left on desktop.
- A call status and saved-memory summary panel floats to the right on desktop.
- Panels stack around the voice stage on narrow screens.
- No query-and-response log table is included.

### Transcript dock

- The live transcript sits in an expandable bottom dock.
- User and agent messages have visually distinct treatments.
- The transcript preserves the generated script: English remains English, Hindi remains Devanagari, and Hinglish remains Roman script.
- The dock remains usable after the call ends.

## Visual System

- Background: near-black navy with restrained atmospheric depth.
- Primary: luminous emerald for actions and listening states.
- Secondary: violet for thinking and AI-energy states.
- Warning: amber for weather or recoverable connection warnings.
- Typography: a modern display face for headings and a readable UI family that supports Latin and Devanagari.
- Motion: breathing orb, voice waveform response, subtle background particles, and smooth panel transitions.
- Motion must honor `prefers-reduced-motion`.
- Controls require visible keyboard focus, readable contrast, and large touch targets.

## Language Routing

Language is detected independently for every completed user turn.

### English

If a turn is clearly English, the assistant replies only in English.

### Hindi

If a turn contains meaningful Devanagari text, the assistant replies in Hindi using Devanagari.

### Hinglish

If a turn uses Roman Hindi or a meaningful mix of Roman Hindi and English, the assistant replies naturally in Hinglish using Roman script. It must not convert a Hinglish response into Devanagari.

### Detection approach

Use a hybrid deterministic classifier:

1. Detect Devanagari script for Hindi.
2. Detect common Roman Hindi vocabulary and phrase patterns for Hinglish.
3. Treat strong English-only text as English.
4. For low-confidence mixed text, instruct the model to mirror the user's vocabulary and script rather than forcing one language.

The per-turn system instruction overrides greeting language, earlier messages, saved language preference, and tool-output prose. Numeric tool values and timestamps remain exact.

## Existing Capabilities Preserved

- LiveKit voice session lifecycle.
- Deepgram multilingual speech recognition.
- Murf Falcon speech synthesis.
- Current India time tool.
- Live district weather tool.
- Caller profile and consent-based conversation memory.
- Microphone permission handling.
- Silence timeout and graceful call ending.
- English and Hindi behavior already implemented.

## Failure Handling

- Microphone denial: show clear permission-recovery instructions without breaking the page.
- Connection failure: show a retryable visible state and do not leave the orb appearing active.
- Weather failure: show and speak that live data is unavailable; never invent conditions.
- Memory failure: say the profile cannot be retrieved or saved right now; never claim success.
- Ambiguous language: mirror the user's script and wording as closely as possible.
- Tool values: never round, translate, or reinterpret exact time and weather numbers.

## Responsive Behavior

- Desktop: full-width website composition with left weather panel, centered orb, and right status/memory panel.
- Tablet: retain the central orb and move support panels into a balanced two-column row.
- Mobile: stack navigation, voice stage, support panels, and transcript without horizontal overflow.
- The primary call control must remain visible and easy to reach at every supported size.

## Testing and Acceptance Criteria

### Language tests

- English input produces an English-only turn instruction.
- Devanagari input produces a Hindi-only turn instruction.
- Roman Hindi input such as `kal baarish hogi kya` produces a Hinglish instruction.
- Mixed input such as `Aaj weather kaisa hai` produces a Hinglish instruction.
- Tool values remain exact in all three modes.

### Frontend checks

- Ready, connecting, active-call, speaking, ended, and microphone-error states render correctly.
- Start and End Call controls still operate.
- Transcript expansion works and messages remain readable.
- Weather and memory panels do not obscure the voice stage.
- Desktop and mobile layouts have no clipping or horizontal overflow.
- Reduced-motion mode removes nonessential animation.
- No query-log table or polling returns.
- Browser console has no relevant errors or warnings.

### Completion standard

The implementation is complete when the agent consistently mirrors English, Hindi, and Hinglish per turn, and the accepted Immersive Voice Portal design is faithfully rendered and validated in the browser on desktop and mobile.
