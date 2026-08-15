# Immersive Hinglish Voice Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reliable per-turn English/Hindi/Hinglish response routing and replace the current narrow voice screen with the approved responsive Immersive Voice Portal website.

**Architecture:** Put deterministic language classification in a focused backend module and let `Assistant.on_user_turn_completed` inject one exact instruction per turn. On the frontend, preserve the existing LiveKit hooks and call handlers while extracting voice-state metadata and the animated orb into focused components, then compose them in a desktop-first portal layout with responsive support panels and a transcript dock.

**Tech Stack:** Python 3.14, LiveKit Agents, pytest, Ruff, Next.js 15, React 19, TypeScript, CSS Modules, LiveKit React components, Browser/IAB validation.

## Global Constraints

- Preserve all existing memory, live weather, India time, microphone handling, silence timeout, Murf Falcon, and LiveKit session behavior.
- Detect response language independently for every completed user turn.
- Devanagari input replies in Devanagari Hindi; clear English replies in English; Roman Hindi or English/Hindi mixing replies in Roman-script Hinglish.
- Preserve exact numeric values and timestamps returned by tools in every language mode.
- Use the approved Immersive Voice Portal visual direction: near-black navy, luminous emerald, violet AI energy, and limited amber warnings.
- Do not restore the query-and-response log table or `/api/queries` polling.
- Honor `prefers-reduced-motion`, keyboard focus visibility, readable contrast, and large touch targets.
- Keep existing dirty-worktree changes intact and stage only files named by each task.

---

### Task 1: Deterministic response-language classifier

**Files:**
- Create: `backend/src/language.py`
- Create: `backend/tests/test_language.py`

**Interfaces:**
- Produces: `ResponseLanguage(str, Enum)` with `ENGLISH`, `HINDI`, `HINGLISH`, and `MIRROR`.
- Produces: `detect_response_language(text: str) -> ResponseLanguage`.
- Produces: `response_language_instruction(mode: ResponseLanguage) -> str`.

- [ ] **Step 1: Write failing classifier tests**

```python
from language import (
    ResponseLanguage,
    detect_response_language,
    response_language_instruction,
)


def test_detects_clear_english() -> None:
    assert detect_response_language("What is today's weather in Lucknow?") is ResponseLanguage.ENGLISH


def test_detects_devanagari_hindi() -> None:
    assert detect_response_language("आज लखनऊ में मौसम कैसा है?") is ResponseLanguage.HINDI


def test_detects_roman_hindi_as_hinglish() -> None:
    assert detect_response_language("kal baarish hogi kya") is ResponseLanguage.HINGLISH


def test_detects_mixed_english_and_roman_hindi_as_hinglish() -> None:
    assert detect_response_language("Aaj weather kaisa hai") is ResponseLanguage.HINGLISH


def test_short_ambiguous_roman_word_uses_mirror_mode() -> None:
    assert detect_response_language("kal") is ResponseLanguage.MIRROR


def test_hinglish_instruction_requires_roman_script_and_exact_values() -> None:
    instruction = response_language_instruction(ResponseLanguage.HINGLISH)
    assert "Hinglish" in instruction
    assert "Roman script" in instruction
    assert "numeric value and time" in instruction
```

- [ ] **Step 2: Run the tests and verify the import fails**

Run: `cd backend && uv run pytest -q tests/test_language.py`

Expected: FAIL because `language.py` does not exist.

- [ ] **Step 3: Implement the minimal classifier and instruction builder**

```python
import re
from enum import Enum


class ResponseLanguage(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"
    MIRROR = "mirror"


ROMAN_HINDI_MARKERS = frozenset(
    {
        "aaj", "kal", "kya", "kaisa", "kaisi", "kaise", "hai", "hain",
        "hoga", "hogi", "mujhe", "mera", "meri", "aap", "batao", "nahi",
        "aur", "mein", "main", "se", "ko", "ki", "ka", "ke", "baarish",
        "mausam", "fasal", "kheti", "pani", "paani", "karna", "karo",
        "rakho", "yaad", "chahiye",
    }
)


def detect_response_language(text: str) -> ResponseLanguage:
    if any("\u0900" <= character <= "\u097f" for character in text):
        return ResponseLanguage.HINDI

    tokens = re.findall(r"[a-z]+", text.casefold())
    marker_count = sum(token in ROMAN_HINDI_MARKERS for token in tokens)
    if marker_count >= 2:
        return ResponseLanguage.HINGLISH
    if marker_count == 1 and len(tokens) > 1:
        return ResponseLanguage.HINGLISH
    if marker_count == 1:
        return ResponseLanguage.MIRROR
    return ResponseLanguage.ENGLISH
```

Implement `response_language_instruction` with fixed strings:

```python
_EXACT_VALUES = (
    " Preserve every numeric value and time from tool results exactly; "
    "do not round or reinterpret them."
)

_INSTRUCTIONS = {
    ResponseLanguage.ENGLISH: (
        "The user's latest turn is English. Reply only in English for this turn, "
        "regardless of the greeting, earlier messages, saved language, or tool "
        "output language." + _EXACT_VALUES
    ),
    ResponseLanguage.HINDI: (
        "The user's latest turn is Hindi. Reply only in Hindi written in "
        "Devanagari for this turn, regardless of the greeting, earlier messages, "
        "saved language, or tool output language." + _EXACT_VALUES
    ),
    ResponseLanguage.HINGLISH: (
        "The user's latest turn is Hinglish. Reply naturally in Hinglish using "
        "Roman script for this turn. Do not switch to Devanagari unless quoting "
        "the caller. The greeting, earlier messages, saved language, and tool "
        "output language must not override the latest turn." + _EXACT_VALUES
    ),
    ResponseLanguage.MIRROR: (
        "The user's latest turn is too short to classify confidently. Mirror the "
        "caller's vocabulary and script for this turn instead of forcing English "
        "or Hindi. Earlier context and saved language must not override it."
        + _EXACT_VALUES
    ),
}


def response_language_instruction(mode: ResponseLanguage) -> str:
    return _INSTRUCTIONS[mode]
```

- [ ] **Step 4: Run focused tests and lint**

Run: `cd backend && uv run pytest -q tests/test_language.py && uv run ruff check src/language.py tests/test_language.py`

Expected: all tests pass and Ruff reports no errors.

- [ ] **Step 5: Commit the classifier**

```bash
git add backend/src/language.py backend/tests/test_language.py
git commit -m "feat: detect English Hindi and Hinglish turns"
```

---

### Task 2: Connect Hinglish routing to the live agent

**Files:**
- Modify: `backend/src/agent.py:36-139`
- Modify: `backend/tests/test_agent.py:97-158`

**Interfaces:**
- Consumes: `detect_response_language(text)` and `response_language_instruction(mode)` from Task 1.
- Preserves: `Assistant.on_user_turn_completed(turn_ctx, new_message) -> None`.

- [ ] **Step 1: Replace brittle exact-string tests with mode-focused failing tests**

Keep the existing English and Hindi cases, but assert the injected message contains the correct mode and script. Add:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    ["kal baarish hogi kya", "Aaj weather kaisa hai"],
)
async def test_latest_hinglish_turn_forces_roman_hinglish_response(text: str) -> None:
    assistant = Assistant()
    turn_context = RecordingTurnContext()
    message = SimpleNamespace(text_content=text)

    await assistant.on_user_turn_completed(turn_context, message)

    instruction = turn_context.messages[0][1]
    assert "latest turn is Hinglish" in instruction
    assert "Roman script" in instruction
    assert "numeric value and time" in instruction
```

Add a mirror-mode test for `"kal"` that asserts the instruction says to mirror the caller's vocabulary and script.

- [ ] **Step 2: Run focused agent tests and verify Hinglish fails**

Run: `cd backend && uv run pytest -q tests/test_agent.py -k "latest or hinglish or mirror"`

Expected: Hinglish and mirror tests fail because all non-Devanagari turns currently become English.

- [ ] **Step 3: Integrate the classifier**

```python
from language import detect_response_language, response_language_instruction


async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
    latest_text = new_message.text_content or ""
    mode = detect_response_language(latest_text)
    turn_ctx.add_message(
        role="system",
        content=response_language_instruction(mode),
    )
```

Update `SYSTEM_PROMPT` so its LANGUAGE section documents English, Hindi, and Roman-script Hinglish rather than treating every Latin-script turn as English. Add a Hinglish out-of-scope fallback: `Main sirf farming aur weather ke sawaalon mein help kar sakti hoon.`

- [ ] **Step 4: Run deterministic backend regression tests**

Run: `cd backend && uv run pytest -q tests/test_language.py tests/test_db.py tests/test_weather.py tests/test_agent.py -k "not offers_assistance and not grounding and not refuses_harmful_request"`

Expected: all deterministic tests pass.

- [ ] **Step 5: Run Ruff and commit**

```bash
cd backend
uv run ruff check src tests
git add src/agent.py tests/test_agent.py
git commit -m "feat: mirror Hinglish in live voice turns"
```

---

### Task 3: Produce the final visual fidelity reference

**Files:**
- Reference: `docs/superpowers/specs/2026-08-10-immersive-hinglish-voice-portal-design.md`
- Reference: `.superpowers/brainstorm/3218-1786354106/content/website-layout.html`
- Create: a desktop concept image and a mobile concept image outside committed source, retaining their absolute paths for final comparison.

**Interfaces:**
- Produces: accepted desktop and mobile image paths used by Tasks 5-7.

- [ ] **Step 1: Read the installed Image Gen skill completely**

Use the `imagegen` skill before calling the image-generation tool.

- [ ] **Step 2: Generate a complete desktop website concept**

Use this exact brief, supplemented only with implementation-safe detail from the approved spec:

```text
Create a complete 1440x1000 desktop product UI concept for Kisan Sahayak, an Indian farming voice assistant. Futuristic immersive AI voice portal, near-black navy background, luminous emerald primary energy, violet AI glow, limited amber weather warnings. Full-width website layout: compact top navigation with Kisan Sahayak identity, connection state, and reset memory; large animated-looking energy orb centered as the main voice stage; live weather floating panel on the left; call status and memory summary floating panel on the right; one prominent Start Call control; expandable transcript dock across the bottom. Show English, हिंदी, and Hinglish as automatically supported, not as manual language tabs. Keep all real controls and text code-native. No query logs, no analytics cards, no marketing sections, no hero eyebrow, no generic dashboard grid. High contrast, spacious, premium, practical to implement in React and CSS.
```

- [ ] **Step 3: Generate a coordinated mobile concept**

Request the same design system at 390x844, stacking navigation, orb, call control, support panels, and transcript without horizontal overflow.

- [ ] **Step 4: Inspect both concepts**

Use `view_image` on both images. Reject and regenerate if controls are unreadable, the orb is not dominant, panels resemble a generic dashboard, or the mobile layout clips.

- [ ] **Step 5: Record the accepted paths in the execution notes**

Do not add generated QA or concept artifacts to the repository unless the user explicitly asks.

---

### Task 4: Add safe profile-summary retrieval for the memory panel

**Files:**
- Modify: `frontend/app/api/profile/route.ts`
- Create: `frontend/lib/caller-profile.ts`

**Interfaces:**
- Produces: `GET /api/profile?user_id=<id>` returning `CallerProfileSummary | null`.
- Produces: `CallerProfileSummary` with `name`, `crops_grown`, `district`, `conversation_memory`, and `last_interaction` nullable strings.
- Produces: `getStoredCallerId() -> string | null` and `fetchCallerProfile(userId: string, signal?: AbortSignal) -> Promise<CallerProfileSummary | null>`.

- [ ] **Step 1: Create the typed client contract**

```ts
export interface CallerProfileSummary {
  name: string | null;
  crops_grown: string | null;
  district: string | null;
  conversation_memory: string | null;
  last_interaction: string | null;
}

export function getStoredCallerId(): string | null {
  return typeof window === 'undefined' ? null : localStorage.getItem('user_id');
}
```

`fetchCallerProfile` must return `null` for 404, throw for other non-OK responses, and pass the optional `AbortSignal` to `fetch`.

- [ ] **Step 2: Add a GET handler without shell-string execution**

Use `child_process.execFile` with SQLite arguments rather than `exec`:

```ts
function readProfile(userId: string): Promise<CallerProfileSummary | null> {
  const sql = `SELECT name, crops_grown, district, conversation_memory, last_interaction FROM callers WHERE user_id = '${userId}' LIMIT 1;`;
  return new Promise((resolve, reject) => {
    execFile('sqlite3', ['-json', DB_PATH, sql], (error, stdout) => {
      if (error) return reject(error);
      const rows = JSON.parse(stdout || '[]') as CallerProfileSummary[];
      resolve(rows[0] ?? null);
    });
  });
}

export async function GET(req: Request) {
  const userId = new URL(req.url).searchParams.get('user_id');
  if (!userId || !/^[a-zA-Z0-9_]+$/.test(userId)) {
    return new NextResponse('Bad Request: Invalid user_id', { status: 400 });
  }
  try {
    const profile = await readProfile(userId);
    return profile
      ? NextResponse.json(profile)
      : new NextResponse('Profile not found', { status: 404 });
  } catch (error) {
    console.error('Failed to read profile:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
```

Reuse the existing strict `/^[a-zA-Z0-9_]+$/` identity validation before constructing `sql`. Select only the five public summary columns. Do not return irrigation, land size, or language preference to this panel.

- [ ] **Step 3: Convert DELETE to `execFile` in the same focused safety change**

Keep current DELETE behavior and response shapes, but remove shell interpolation through `exec`.

- [ ] **Step 4: Run TypeScript and exercise the route**

Run: `cd frontend && pnpm exec tsc --noEmit`

With the app running, run: `curl -sS -o /tmp/kisan-profile.json -w '%{http_code}' 'http://localhost:3000/api/profile?user_id=farmer_923327'`

Expected: HTTP `200` with a JSON object when the row exists, or `404` when it does not; never `500` for a valid missing ID.

- [ ] **Step 5: Commit the profile contract**

```bash
git add frontend/app/api/profile/route.ts frontend/lib/caller-profile.ts
git commit -m "feat: expose safe caller memory summary"
```

---

### Task 5: Extract voice-state metadata and build the animated orb

**Files:**
- Create: `frontend/components/app/voice-portal/voice-state.ts`
- Create: `frontend/components/app/voice-portal/voice-orb.tsx`
- Create: `frontend/components/app/voice-portal/voice-portal.module.css`
- Modify: `frontend/components/app/kisan-sahayak-view.tsx`

**Interfaces:**
- Produces: `VoiceState = 'ready' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ended'`.
- Produces: `VOICE_STATE_CONTENT: Record<VoiceState, { label: string; hindiLabel: string; hint: string; tone: 'emerald' | 'violet' | 'amber' | 'muted' }>`.
- Produces: `<VoiceOrb state userVolume agentVolume />`.

- [ ] **Step 1: Extract the state type and copy into a pure module**

Move the current `STATES` content into `VOICE_STATE_CONTENT`, updating tones to the approved palette. Keep Ready bilingual. Connected state copy remains bilingual until a transcript turn establishes a language.

- [ ] **Step 2: Build `VoiceOrb` around the real audio volumes**

```tsx
interface VoiceOrbProps {
  state: VoiceState;
  userVolume: number;
  agentVolume: number;
}

export function VoiceOrb({ state, userVolume, agentVolume }: VoiceOrbProps) {
  const raysRef = useRef<SVGLineElement[]>([]);
  const volumeRef = useRef({ userVolume, agentVolume });

  useEffect(() => {
    volumeRef.current = { userVolume, agentVolume };
  }, [userVolume, agentVolume]);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let frame = 0;
    let phase = 0;
    const tick = () => {
      phase += 0.045;
      const liveVolume = state === 'speaking'
        ? volumeRef.current.agentVolume
        : volumeRef.current.userVolume;
      raysRef.current.forEach((ray, index) => {
        const angle = (index / 32) * Math.PI * 2;
        const pulse = 10 + Math.sin(phase * 3 + index * 0.7) * 5 + liveVolume * 36;
        ray.setAttribute('x2', String(120 + Math.cos(angle) * (76 + pulse)));
        ray.setAttribute('y2', String(120 + Math.sin(angle) * (76 + pulse)));
      });
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [state]);

  return (
    <div className={styles.orb} data-state={state}>
      <svg aria-hidden="true" viewBox="0 0 240 240" className={styles.rays}>
        {Array.from({ length: 32 }, (_, index) => {
          const angle = (index / 32) * Math.PI * 2;
          const x = 120 + Math.cos(angle) * 76;
          const y = 120 + Math.sin(angle) * 76;
          return <line key={index} ref={(node) => { if (node) raysRef.current[index] = node; }} x1={x} y1={y} x2={x} y2={y} />;
        })}
      </svg>
      <div className={styles.orbCore}><span className={styles.orbGlyph}>✦</span></div>
    </div>
  );
}
```

Move `raysRef`, `animationFrameRef`, and the volume-driven ray loop out of the page component. Stop the animation loop under `prefers-reduced-motion: reduce`, leaving a static luminous orb.

- [ ] **Step 3: Add design tokens and orb styles**

Define module-level custom properties and state styles:

```css
.portal {
  --portal-bg: #060912;
  --portal-panel: rgba(13, 20, 34, 0.72);
  --portal-emerald: #42f59e;
  --portal-violet: #8b6cff;
  --portal-amber: #f4b860;
  --portal-text: #f4fff9;
  --portal-muted: #94a9a1;
  --portal-border: rgba(125, 255, 194, 0.16);
  --portal-focus: 0 0 0 3px rgba(66, 245, 158, 0.42);
  min-height: 100svh;
  background: var(--portal-bg);
  color: var(--portal-text);
}

.orb[data-state='thinking'] { --orb-color: var(--portal-violet); }
.orb[data-state='connecting'], .orb[data-state='listening'] { --orb-color: var(--portal-amber); }
.orb[data-state='ready'], .orb[data-state='speaking'] { --orb-color: var(--portal-emerald); }
.orb[data-state='ended'] { --orb-color: var(--portal-muted); }

@media (prefers-reduced-motion: reduce) {
  .orb, .orbCore, .rays { animation: none !important; transition: none !important; }
}
```

- [ ] **Step 4: Replace the inline orb implementation in the page**

Import `VoiceOrb`, `VoiceState`, and `VOICE_STATE_CONTENT`; preserve the existing LiveKit-derived `currentState`, `userVolume`, and `agentVolume` values.

- [ ] **Step 5: Run typecheck and inspect the first viewport**

Run: `cd frontend && pnpm exec tsc --noEmit`

Reload Browser/IAB at `http://localhost:3000/`. Expected: the page loads without a framework overlay, the orb renders, and Start Call remains visible.

- [ ] **Step 6: Commit the orb extraction**

```bash
git add frontend/components/app/voice-portal frontend/components/app/kisan-sahayak-view.tsx
git commit -m "refactor: extract immersive voice orb"
```

---

### Task 6: Compose the full website-format portal

**Files:**
- Create: `frontend/components/app/voice-portal/weather-panel.tsx`
- Create: `frontend/components/app/voice-portal/memory-panel.tsx`
- Create: `frontend/components/app/voice-portal/transcript-dock.tsx`
- Modify: `frontend/components/app/kisan-sahayak-view.tsx`
- Modify: `frontend/components/app/app.tsx:65-79`
- Modify: `frontend/components/app/voice-portal/voice-portal.module.css`

**Interfaces:**
- Consumes: `CallerProfileSummary`, `VoiceState`, LiveKit `messages`, current weather strings, and existing call handlers.
- Produces: desktop grid areas `weather`, `voice`, `memory`, and `transcript` with stacked mobile behavior.

- [ ] **Step 1: Build focused display components**

```tsx
export function WeatherPanel(props: {
  temperature: string;
  condition: string;
  location: string;
  advisory: string;
}) {
  return (
    <section className={styles.panel} data-testid="weather-panel" aria-labelledby="weather-title">
      <p className={styles.panelLabel} id="weather-title">Live weather</p>
      <p className={styles.weatherReading}>{props.temperature}</p>
      <p>{props.condition} · {props.location}</p>
      <p className={styles.advisory}>{props.advisory}</p>
    </section>
  );
}

export function MemoryPanel(props: {
  profile: CallerProfileSummary | null;
  loading: boolean;
}) {
  if (props.loading) return <section className={styles.panel} aria-busy="true">Loading memory…</section>;
  return (
    <section className={styles.panel} aria-labelledby="memory-title">
      <p className={styles.panelLabel} id="memory-title">Saved memory</p>
      {props.profile ? (
        <>
          <p>{props.profile.crops_grown || 'No crops saved'} · {props.profile.district || 'No district saved'}</p>
          <p className={styles.memorySummary}>{props.profile.conversation_memory || 'No conversation summary saved'}</p>
        </>
      ) : <p>No saved profile found</p>}
    </section>
  );
}

export interface TranscriptMessage {
  id: string;
  message: string;
  from?: { isLocal?: boolean };
}

export function TranscriptDock(props: {
  open: boolean;
  onToggle: () => void;
  messages: readonly TranscriptMessage[];
}) {
  return (
    <section className={styles.transcriptDock}>
      <button type="button" onClick={props.onToggle} aria-expanded={props.open} aria-controls="voice-transcript">
        Conversation transcript
      </button>
      <div id="voice-transcript" hidden={!props.open} role="log" aria-live="polite">
        {props.messages.map((item) => (
          <p key={item.id} className={item.from?.isLocal ? styles.userMessage : styles.agentMessage}>
            <strong>{item.from?.isLocal ? 'You' : 'Kisan Sahayak'}</strong> {item.message}
          </p>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Fetch profile memory once per caller identity**

In `KisanSahayakView`, fetch once with cancellation and no polling:

```tsx
useEffect(() => {
  const userId = getStoredCallerId();
  if (!userId) {
    setProfileLoading(false);
    return;
  }
  const controller = new AbortController();
  fetchCallerProfile(userId, controller.signal)
    .then(setCallerProfile)
    .catch((error: unknown) => {
      if ((error as Error).name !== 'AbortError') console.warn('Profile summary unavailable');
    })
    .finally(() => setProfileLoading(false));
  return () => controller.abort();
}, []);
```

- [ ] **Step 3: Replace the current single-column markup**

Compose:

```tsx
<div className={styles.portal} data-state={currentState}>
  <header className={styles.topbar}>
    <a className={styles.brand} href="/" aria-label="Kisan Sahayak home">Kisan Sahayak</a>
    <div className={styles.topbarActions}>
      <span className={styles.connectionState}>{session.isConnected ? 'Connected' : 'Disconnected'}</span>
      <button type="button" onClick={handleResetMemory}>Reset memory</button>
    </div>
  </header>
  <main className={styles.portalGrid}>
    <WeatherPanel temperature={temp} condition={weatherText} location={detectedLocation.split(',')[0]} advisory={advisory} />
    <section className={styles.voiceStage} aria-labelledby="voice-state-title">
      <VoiceOrb state={currentState} userVolume={userVolume} agentVolume={agentVolume} />
      <h1 id="voice-state-title">{activeState.label}</h1>
      <p>{activeState.hindiLabel}</p>
      {currentState === 'ready' && <button type="button" onClick={handleTalkClick}>Start Call / बातचीत शुरू करें</button>}
      {currentState === 'ended' && <button type="button" onClick={handleStartAgain}>Start Again / फिर से शुरू करें</button>}
      {session.isConnected && <button type="button" onClick={() => session.end?.()}>End Call / कॉल समाप्त करें</button>}
    </section>
    <MemoryPanel profile={callerProfile} loading={profileLoading} />
    <TranscriptDock open={transcriptOpen} onToggle={() => setTranscriptOpen((open) => !open)} messages={messages} />
  </main>
</div>
```

Keep the existing Start Call, Start Again, End Call, microphone retry, and Reset Memory handlers. Remove the manual EN/हिं toggle because response language is automatic. Do not add analytics, log history, or marketing sections.

- [ ] **Step 4: Make the app wrapper website-sized**

Replace the centered `place-content-center` wrapper in `app.tsx` with a full-width, full-height wrapper that does not constrain the portal.

- [ ] **Step 5: Run typecheck and source regressions**

Run: `cd frontend && pnpm exec tsc --noEmit`

Run: `rg -n "Query & Response Logs|queriesHistory|fetchQueriesHistory|/api/queries|lang-toggle" frontend/components/app`

Expected: no matches for removed log polling or the manual language toggle.

- [ ] **Step 6: Commit the portal composition**

```bash
git add frontend/components/app/app.tsx frontend/components/app/kisan-sahayak-view.tsx frontend/components/app/voice-portal
git commit -m "feat: build immersive voice portal website"
```

---

### Task 7: Responsive, accessibility, and visual fidelity pass

**Files:**
- Modify: `frontend/components/app/voice-portal/voice-portal.module.css`
- Modify if browser findings require semantic or state fixes: `frontend/components/app/voice-portal/voice-orb.tsx`
- Modify if browser findings require semantic or state fixes: `frontend/components/app/voice-portal/weather-panel.tsx`
- Modify if browser findings require semantic or state fixes: `frontend/components/app/voice-portal/memory-panel.tsx`
- Modify if browser findings require semantic or state fixes: `frontend/components/app/voice-portal/transcript-dock.tsx`

**Interfaces:**
- Consumes: accepted desktop/mobile concept paths from Task 3.
- Produces: agency-signoff desktop and mobile renders.

- [ ] **Step 1: Validate the desktop core flow in Browser/IAB**

At `http://localhost:3000/`, verify page title, meaningful DOM, no framework overlay, zero console errors/warnings, and screenshot evidence. Click Start Call only if microphone permission is already granted; otherwise exercise the transcript toggle and Reset Memory focus state without confirming deletion.

- [ ] **Step 2: Compare desktop render with the accepted concept**

Capture the implementation at the concept's native size when supported. Use `view_image` on the accepted desktop concept and saved browser screenshot. Record and fix mismatches for at least: page structure, orb scale, palette, typography, panel placement, call-control prominence, and transcript anatomy.

- [ ] **Step 3: Validate mobile at 390x844**

Use the Browser viewport capability. Verify no horizontal overflow, readable labels, reachable call control, stacked panels, transcript expansion, and no panel overlap. Capture a screenshot and compare it with the accepted mobile concept using `view_image`.

- [ ] **Step 4: Validate reduced motion and keyboard focus**

Confirm `@media (prefers-reduced-motion: reduce)` disables ray/particle transitions. Tab through Reset Memory, Start/End Call, microphone retry when present, and transcript toggle; every control must have a visible focus ring.

- [ ] **Step 5: Run final frontend checks**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm exec prettier --check components/app/voice-portal components/app/kisan-sahayak-view.tsx components/app/app.tsx lib/caller-profile.ts app/api/profile/route.ts`

Expected: TypeScript and formatting checks pass. If the pre-existing main component formatting differs, format only files changed by this plan and review the resulting diff before keeping it.

- [ ] **Step 6: Commit fidelity fixes**

```bash
git add frontend/components/app/voice-portal frontend/components/app/kisan-sahayak-view.tsx
git commit -m "fix: polish responsive portal states"
```

---

### Task 8: Full regression and live smoke test

**Files:**
- Modify: `README.md` only if the documented language support still says English/Hindi only.
- Modify: `backend/README.md` only if its language section is stale.

**Interfaces:**
- Verifies all interfaces produced in Tasks 1-7.

- [ ] **Step 1: Run the complete deterministic backend suite**

Run: `cd backend && uv run pytest -q tests/test_language.py tests/test_db.py tests/test_weather.py tests/test_agent.py -k "not offers_assistance and not grounding and not refuses_harmful_request" && uv run ruff check src tests`

Expected: all deterministic tests and lint pass.

- [ ] **Step 2: Run final frontend type and diff checks**

Run: `cd frontend && pnpm exec tsc --noEmit`

Run: `git diff --check`

Expected: both exit successfully.

- [ ] **Step 3: Restart the application using the project launcher**

Run: `cd /Users/reetsingh/Desktop/suar && ./start_app.sh`

Expected: frontend serves `http://localhost:3000/` and the LiveKit agent worker registers successfully.

- [ ] **Step 4: Exercise one question in each language mode**

Ask these exact questions in separate turns:

```text
What is the current time in India?
भारत में अभी समय क्या है?
Aaj India mein current time kya hai?
```

Expected: English, Devanagari Hindi, and Roman Hinglish responses respectively; all repeat the exact same live tool time format without rounding.

- [ ] **Step 5: Verify memory and weather regressions**

Ask what the agent remembers and one current-weather question. Confirm memory retrieval still calls the profile tool and current weather still calls the live weather tool with a timestamped response or graceful failure.

- [ ] **Step 6: Update stale documentation and commit final verification changes**

```bash
git add README.md backend/README.md
git commit -m "docs: document Hinglish voice support"
```

Skip the commit if neither README requires a change.
