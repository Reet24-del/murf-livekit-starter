# Farm & Field Voice Assistant — #VoiceForBharat Edition

A voice AI assistant designed to help Indian farmers with crop management, soil health, weather advisories, and farming techniques. Built for the **Farm & Field** track of the **10 Days of Voice Agents (#VoiceForBharat)** challenge.

This agent connects speech-to-text (STT), a large language model (LLM), and text-to-speech (TTS) around a WebRTC transport layer to enable low-latency, natural, voice-based interactions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Murf Falcon](https://img.shields.io/badge/TTS-Murf%20Falcon-6366F1)](https://murf.ai/api/docs/text-to-speech/streaming) [![LiveKit](https://img.shields.io/badge/Transport-LiveKit-002cf2)](https://docs.livekit.io) [![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white)](https://www.typescriptlang.org/) [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## Performance Metrics (Day 1 Benchmark)

*   **Model Latency (Murf Falcon)**: ~55ms
*   **Time-to-First-Audio (TTFB)**: logged at **137ms – 263ms** average
*   **STT Provider**: Deepgram Nova-3
*   **LLM Provider**: Google Gemini (`gemini-3.5-flash-lite`)
*   **TTS Provider**: Murf Falcon (Indian English Voice `Anisha`)

## Day 5: Live District Weather Tool

Kisan Sahayak includes a `get_district_weather` function tool backed by the live [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) and [Forecast API](https://open-meteo.com/en/docs). This is live external data, not a hand-built local dataset.

The tool resolves an Indian district and returns:

- Current temperature, weather condition, and wind speed
- Today's minimum and maximum temperature
- Today's maximum probability of rain
- The local observation time and forecast date

If the farmer does not name a district, the tool first reuses their saved Day 4 district and then checks their LiveKit participant location. Requests time out after eight seconds. If Open-Meteo is unavailable, the agent explicitly says live weather is unavailable and does not invent a temperature or forecast.

Try this after saving a district in the caller profile:

> “क्या आज कपास पर दवा छिड़कने के लिए मौसम ठीक है?”

Or name the location directly:

> “What is today's rain chance in Wardha?”

## Day 6: Outbound Rain-Advisory Calls

Kisan Sahayak has a separate `outbound-agent` worker that calls a user-controlled [Linphone](https://www.linphone.org/) account through LiveKit SIP. It immediately identifies itself, explains that it is calling with a rain and crop-safety advisory, and tells the recipient how to stop future calls. The advisory uses live Open-Meteo data fetched during the call and spoken with Murf Falcon using the Anisha voice.

The workflow includes:

- English openings and replies for English callers
- Hindi written only in Devanagari, including replies to Roman Hindi
- Persistent opt-out storage in SQLite
- Busy, declined, timeout, voicemail, and missing-data handling
- Consent confirmation and 08:00–20:00 IST calling hours before dispatch

### One-time Linphone setup

1. Create a free account at [subscribe.linphone.org](https://subscribe.linphone.org/register/email) and note only the username portion of `sip:USERNAME@sip.linphone.org`.
2. Install the Linphone phone app, sign in, allow microphone access, then turn **Settings → Calls → Advanced calls settings → Media encryption mandatory** off.
3. In **LiveKit Cloud → Telephony → SIP Trunks**, create an outbound trunk using [`backend/src/telephony/outbound/linphone-trunk.example.json`](backend/src/telephony/outbound/linphone-trunk.example.json). Replace `YOUR_LINPHONE_USERNAME`, save the trunk, and copy its `ST_...` ID.
4. Add the trunk ID to `backend/.env.local`:

```dotenv
LIVEKIT_SIP_OUTBOUND_TRUNK_ID=ST_your_real_trunk_id
```

### Start and test the outbound workflow

From `backend/`, start the dedicated worker:

```bash
uv run python -m telephony.outbound.agent dev
```

In another terminal, validate everything without contacting LiveKit:

```bash
uv run python -m telephony.outbound.dial \
  --to YOUR_LINPHONE_USERNAME \
  --district Lucknow \
  --crop tomato \
  --language en \
  --consent-confirmed \
  --dry-run
```

Remove `--dry-run` to make the controlled call:

```bash
uv run python -m telephony.outbound.dial \
  --to YOUR_LINPHONE_USERNAME \
  --district Lucknow \
  --crop tomato \
  --language hi \
  --consent-confirmed
```

The destination must belong to you or to a recipient who agreed to the call. The CLI blocks saved opt-outs and calls outside 08:00–20:00 IST; `--override-quiet-hours` exists only for a controlled challenge demonstration. To show graceful live-data failure in the video, make a controlled call with `--district "Not a district"`; the agent says that live weather is unavailable instead of inventing values.


---

## Architecture

```mermaid
flowchart LR
    A[🎙️ User speaks] -->|audio| B[Deepgram STT]
    B -->|text| C[LLM]
    C -->|response text| D[Murf Falcon TTS]
    D -->|audio| E[LiveKit]
    E -->|stream| F[🔊 User hears]

    style A fill:#444441,stroke:#888780,color:#fff
    style B fill:#185FA5,stroke:#85B7EB,color:#fff
    style C fill:#534AB7,stroke:#AFA9EC,color:#fff
    style D fill:#0F6E56,stroke:#5DCAA5,color:#fff
    style E fill:#D85A30,stroke:#F0997B,color:#fff
    style F fill:#444441,stroke:#888780,color:#fff
```

---

## Quickstart

### Prerequisites

- **Python** 3.10+
- **[uv](https://docs.astral.sh/uv/)** - fast Python package manager
  ```bash
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Node.js** 18+
- **pnpm** — fast Node package manager
  ```bash
  npm install -g pnpm
  ```
- A [LiveKit](https://cloud.livekit.io/) project (free tier available)

### Step 1: Clone the repo

```bash
git clone https://github.com/murf-ai/murf-livekit-starter.git
cd murf-livekit-starter
```

### Step 2: Set up environment variables

Create `.env.local` in both `backend/` and `frontend/` (copy from `.env.example` in each). You need:

| Variable                               | Where to get it                                        | Required |
| -------------------------------------- | ------------------------------------------------------ | -------- |
| `LIVEKIT_URL`                          | LiveKit Cloud dashboard                                | Yes      |
| `LIVEKIT_API_KEY`                      | LiveKit Cloud dashboard                                | Yes      |
| `LIVEKIT_API_SECRET`                   | LiveKit Cloud dashboard                                | Yes      |
| `LIVEKIT_SIP_OUTBOUND_TRUNK_ID`        | LiveKit Cloud → Telephony → SIP Trunks                  | Day 6    |
| `MURF_API_KEY`                         | [murf.ai/api/dashboard](https://murf.ai/api/dashboard) | Yes      |
| `DEEPGRAM_API_KEY`                     | [deepgram.com](https://deepgram.com)                   | Yes      |
| `GOOGLE_API_KEY` (or `OPENAI_API_KEY`) | Depends on LLM choice                                  | Yes      |

### Step 3: Install backend dependencies

```bash
cd backend
uv sync
uv run python src/agent.py download-files
```

### Step 4: Install frontend dependencies

```bash
cd frontend
pnpm install
```

### Step 5: Run it

**Option A - All-in-one (from repo root):**

```bash
# macOS/Linux
chmod +x start_app.sh
./start_app.sh

# Windows (PowerShell)
.\start_app.ps1
```

**Option B - Separate terminals:**

```bash
# Terminal 1 — LiveKit Server
livekit-server --dev

# Terminal 2 — Backend agent
cd backend && uv run python src/agent.py dev

# Terminal 3 — Frontend
cd frontend && pnpm dev
```

Then open **http://localhost:3000** in your browser.

You should now see the voice agent UI. Click **Start talking**, allow microphone access, and speak — the agent will respond with Murf Falcon TTS. Ensure your backend and (if using Option B) LiveKit server are running.

---

## Deploy

Want to deploy this beyond localhost? You'll need to deploy **two services**: the backend agent and the frontend. Both must use the same LiveKit project.

> This is a two-service app — the backend agent and the frontend UI deploy separately. You'll need both running and connected to the same LiveKit project.

### Backend (Python agent) — Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1?referralCode=cNjn2P&utm_medium=integration&utm_source=template&utm_campaign=generic)

Set these environment variables in Railway:

- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY` or `OPENAI_API_KEY`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

The backend runs as a long-lived Python process that connects to LiveKit as an agent. Railway handles this well.

### Frontend (Next.js) — Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/murf-ai/murf-livekit-starter&root-directory=frontend&env=LIVEKIT_URL,LIVEKIT_API_KEY,LIVEKIT_API_SECRET&project-name=murf-voice-agent&repository-name=murf-voice-agent)

Set these environment variables in Vercel:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `AGENT_NAME` (optional — for explicit agent dispatch)

The frontend is a standard Next.js app. Point it at the same LiveKit instance your backend agent is connected to.

### Connecting them

The frontend and backend don't call each other directly — they both connect to **LiveKit**, which handles the real-time audio transport.

1. Use the **same** `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` on both Railway and Vercel
2. Set `AGENT_NAME=my-agent` on Vercel — this matches the `agent_name="my-agent"` registered in `backend/src/agent.py`
3. Verify: Railway logs should show the agent connected to LiveKit. Open your Vercel URL, click **Start talking** — the agent should respond

If the agent doesn't connect, double-check that both services point to the same LiveKit project and that the backend is running (check Railway logs).

---

## Current Active Configuration: Farm & Field Track

The agent is configured as **Kisan Sahayak**, a friendly, experienced agricultural expert assisting Indian farmers with crop management, soil health, pest control, and local weather advisories.

**Where the prompt lives:** `backend/src/agent.py` — the `SYSTEM_PROMPT` constant.

### The Active System Prompt

```
IDENTITY:
You are Kisan Sahayak, a friendly and experienced agricultural expert helping Indian farmers. You work for the Krishi Sahayata Center.

OBJECTIVES:
- Understand the farmer's agricultural query (crop selection, soil health, pests, weather).
- Provide practical, easy-to-follow, and direct advice.
- Escalate complex queries warmly to human experts or local authorities.

KNOWLEDGE LIMITS:
- You know about Indian crops, soil care, fertilizers, organic pest control, and regional weather patterns.
- Do NOT make up market prices, subsidy details, or long-term weather predictions (more than 7 days ahead). If asked, explain that you do not have current data for that.
- Do NOT answer questions outside of agriculture, farming, and local weather.

LANGUAGE:
- STRICT LANGUAGE MATCHING: You must instantly adapt to the language of the user's latest turn. If the user switches language in between, you MUST switch with them:
  - If the user speaks to you in English, you MUST reply strictly in English (using standard English text).
  - If the user speaks Hindi in Devanagari, reply in Hindi using Devanagari.
  - If the user speaks Hinglish in Roman script, reply naturally in Roman-script Hinglish and preserve exact numbers, dates, and tool results.
  - If the latest turn is too short or ambiguous to classify safely, mirror its script instead of forcing a different language.
- Speak in a warm, respectful, and polite register. Always use gender-neutral respectful terms like "जी" (ji) or "आप" (aap). NEVER assume the user's gender and NEVER use masculine terms like "भैया" (bhaiya) or "brother" to address the user.
- GENDER: You are a female assistant speaking in a woman's voice. When speaking in Hindi, always use feminine verb endings and pronouns (e.g., use "सकती हूँ" instead of "सकता हूँ", "बोल रही हूँ" instead of "बोल रहा हूँ", "करूँगी" instead of "करूँगा").

GUARDRAILS:
- Refuse out-of-scope queries (general knowledge, political topics, sports, coding, entertainment) politely in Devanagari script: "मैं केवल खेती और मौसम से जुड़े सवालों के जवाब दे सकती हूँ।"
- Never claim to state current live crop market prices as fact. If asked, explain that market rates fluctuate daily and recommend checking local mandis.
- If a query is outside your knowledge limits, use this Devanagari escalation path: "इसके लिए मैं आपको किसान कॉल सेंटर के टोल-फ्री नंबर 1800-180-1551 पर बात करने या अपने स्थानीय कृषि विज्ञान केंद्र (KVK) अधिकारी से संपर्क करने की सलाह दूँगी।"

STYLE:
- Keep your spoken responses very short (maximum 1 to 2 simple sentences, under 25 words).
- Speak slowly and clearly.
- Never use markdown formatting, bullet points, or list structures in your text output (e.g. no bold text, no asterisks, no dashes, no numbers). Write plain text only.
```

---

## Immersive Voice Portal

The frontend is a responsive, voice-first portal for Indian farmers with a neon agricultural visual system, live agent states, saved memory, and microphone error handling:

1. **Branding & Theming**: A full-width dark interface combines emerald and violet energy effects, glass panels, a central reactive voice orb, and bilingual labels.
2. **Five Agent States**:
   - **Ready**: Shows an inviting card greeting, sprout icon, and a single prominent **Start Call / बातचीत शुरू करें** button.
   - **Connecting**: Tells the user to wait while joining the room, showing a spinning and pulsing loader ring around the core.
   - **Listening**: Renders custom radial SVG lines that vibrate in sync with the **farmer's real-time microphone volume**. Displays an active golden-orange badge.
   - **Speaking**: Renders visualizer lines that vibrate in sync with the **agent's real-time voice stream volume** (using Murf Falcon's output). Displays a soft green speaking badge.
   - **Call ended**: Shows "Call Ended / कॉल समाप्त हो गई है", keeps the transcript visible for review, and shows a **Start Again / फिर से शुरू करें** button.
3. **Microphone Permission error handling**: Intercepts `NotAllowedError` during call startup or queries page permissions on mount. If blocked, displays a prominent warning overlay explaining how to open the lock icon (🔒) in the browser address bar and enable microphone permissions, with a **Try Again** button.
4. **Automatic multilingual support**: The backend classifies every latest turn as English, Devanagari Hindi, Roman Hinglish, or ambiguous/mirror mode. There is no manual language toggle.
5. **Memory and data surfaces**: The Saved memory panel reads the caller profile from the local SQLite-backed profile API. The weather panel prompts users to ask for live weather because spoken weather values come from the timestamped Open-Meteo tool rather than a decorative browser-side estimate.
6. **Responsive website layout**: Desktop places weather, the voice stage, and memory side by side; tablet and mobile layouts stack the voice stage first and keep the primary call control full width and reachable.

---

## Configuration

## Day 7: Human-help escalation

Kisan Sahayak now knows when to stop and ask a human for help. It offers an escalation only for a serious or rapidly spreading crop problem (high urgency), or when requested market data is missing or stale (medium urgency). Normal farming, weather, time, and memory questions do not create requests.

Before writing anything, the agent explains that it will share the caller identity and saved name when available, a short problem summary, checks performed, urgency, current language, and the `in_app` follow-up method. It asks for explicit consent in English, Hindi, or Hinglish. A refusal, ambiguous answer, missing identity, or consent value that does not match the caller's latest turn creates no request.

Requests are real local SQLite records in `backend/memory.db`; this demo does not send them to an external help desk. Passwords, OTPs, PINs, account/card numbers, and long digit sequences are replaced with `[REDACTED]`, text is limited to 500 characters, and the full transcript is never stored. Repeated open or in-progress requests for the same caller and reason update the existing reference rather than creating duplicates.

Open the staff dashboard at [http://localhost:3000/help-requests](http://localhost:3000/help-requests). Requests move through `open`, `in_progress`, and `resolved`. The reference format is `KS-YYYYMMDD-XXXX`; it is an honest tracking reference and does not promise an immediate response. If persistence fails, the agent recommends the Kisan Call Center at 1800-180-1551 or the local KVK.

Demo prompts:

- Serious path: “My tomato plants are suddenly black and half the field is dying.” Then: “Yes, create the request.”
- Refusal path: repeat a severe problem, then say “No, do not share it.”
- Normal path: “How often should I water tomatoes?”
- Market path: “What is today's exact tomato mandi price?” Then consent after the agent offers human help.

For the Day 7 video, show the agent identifying the serious case, explaining the fields, asking permission, returning a reference, and the row appearing at `/help-requests`. The LinkedIn post should mention Murf Falcon as the fastest TTS API, **10 Days of Voice Agents**, tag **Murf AI**, and include **#VoiceForBharat**.

### Murf voice

Edit the `tts=murf.TTS(...)` call in `backend/src/agent.py`. Set the `voice` argument to any Murf voice ID. Examples:

- `Anisha` — Indian English (female, default in this starter)
- `Amara` — US English (female)
- `Hazel` — UK English (female)
- `Gordon` — US English (male)

Browse all voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library).

### STT provider

STT is configured in `backend/src/agent.py` in the `AgentSession(stt=...)` call. The default is Deepgram (`deepgram.STT(model="nova-3")`). You can swap to another LiveKit-compatible STT plugin if needed.

### LLM (Gemini vs OpenAI)

- **Gemini (default):** Set `GOOGLE_API_KEY` and use `llm=google.LLM(model="gemini-3.5-flash-lite")` in `agent.py`.
- **OpenAI:** Set `OPENAI_API_KEY`, add the OpenAI plugin, and use the corresponding `llm=openai.LLM(...)` in `agent.py`.

### Audio format

Murf Falcon and LiveKit handle audio format internally. For advanced options, see [Murf API docs](https://murf.ai/api/docs) and [LiveKit docs](https://docs.livekit.io).

---

## Project Structure

```
murf-livekit-starter/
├── backend/                 # Python voice agent (LiveKit Agents + Murf Falcon)
│   ├── src/
│   │   └── agent.py         # Agent entrypoint, pipeline (STT/LLM/TTS), system prompt
│   ├── tests/               # Agent tests
│   ├── .env.example         # Backend env template
│   ├── pyproject.toml       # Python deps (uv)
│   └── railway.toml         # Railway deploy config
├── frontend/                # Next.js UI for voice sessions
│   ├── app/
│   │   ├── page.tsx         # Main page
│   │   └── api/token/       # LiveKit token endpoint (dev)
│   ├── components/          # UI (agents-ui, app config, theme)
│   ├── app-config.ts        # Branding, title, button text, accent
│   ├── .env.example         # Frontend env template
│   └── package.json         # Node deps (pnpm)
├── start_app.sh             # Start LiveKit + backend + frontend (macOS/Linux)
├── start_app.ps1            # Start LiveKit + backend + frontend (Windows)
├── README.md                # This file
```

For deeper documentation on each part, see:

- [Backend Documentation](./backend/README.md) — agent pipeline, voice/LLM/STT configuration, testing, deployment
- [Frontend Documentation](./frontend/README.md) — UI customization, visualizers, theming, component architecture

---

## Links

- [Murf API Docs](https://murf.ai/api/docs)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Docs](https://docs.livekit.io)
- [Deepgram Docs](https://developers.deepgram.com)
- [Murf Falcon Benchmarks](https://murf.ai/falcon/benchmarks)
- [TTS Latency Benchmarker](https://github.com/sahilsgupta/tts-latency-benchmarker) — run your own p50/p95 tests across providers
- [Murf Discord](https://discord.gg/FbKAy96Sz7)
- [Murf Startup Incubator](https://murf.ai/api) — 50M free characters for startups

---

## License

MIT
