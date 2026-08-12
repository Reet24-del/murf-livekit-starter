# Backend — Voice Agent with Murf Falcon TTS

The Python backend for the Voice Agent Starter. It runs a real-time voice AI pipeline using [LiveKit Agents](https://docs.livekit.io/agents), connecting Murf Falcon TTS, Deepgram STT, and Google Gemini into a single conversational agent.

## How It Works

```
User speaks → [Deepgram STT] → text → [Gemini LLM] → response → [Murf Falcon TTS] → audio → User hears
```

### Day 5 live weather data

The agent's `get_district_weather` function calls the live [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) and [Forecast API](https://open-meteo.com/en/docs). The data is fetched at request time; it is not a local sample dataset. Successful results include the local observation time and forecast date along with current temperature, conditions, wind, today's temperature range, and maximum rain probability.

The district is selected in this order: a location named in the current question, the caller's saved Day 4 district, then LiveKit participant location metadata. The request has an eight-second timeout. Unknown districts, timeouts, API errors, and incomplete responses produce a spoken “live data unavailable” message without fabricated weather values.

Demo question: `What is today's rain chance in Wardha?`

LiveKit handles the real-time audio transport. The agent connects to LiveKit as a participant, listens for user speech, and responds with synthesized audio.

### Day 6 outbound calls with Linphone

The separate `outbound-agent` worker places a consented LiveKit SIP call to a controlled Linphone account and delivers a live rain advisory. The first two sentences are fixed so the recipient immediately hears who is calling, why Kisan Sahayak is calling, and how to stop future calls. English stays English; Hindi and Roman Hindi receive Devanagari Hindi. Opt-outs are persisted in `memory.db` and checked before every later dispatch.

Linphone and LiveKit SIP are live external services. Open-Meteo is queried at call time, so a weather outage produces a spoken unavailable-data fallback rather than a fabricated advisory.

#### Configure Linphone and the SIP trunk

1. Create a free [Linphone account](https://subscribe.linphone.org/register/email). Its SIP address looks like `sip:USERNAME@sip.linphone.org`.
2. Install the Linphone phone app and sign in. Allow microphone access and turn **Settings → Calls → Advanced calls settings → Media encryption mandatory** off.
3. Open **LiveKit Cloud → Telephony → SIP Trunks** and create an outbound trunk from `src/telephony/outbound/linphone-trunk.example.json`, replacing `YOUR_LINPHONE_USERNAME`.
4. Copy the generated trunk ID into `.env.local`:

```dotenv
LIVEKIT_SIP_OUTBOUND_TRUNK_ID=ST_your_real_trunk_id
```

#### Run the worker and call your account

Terminal one:

```bash
uv run python -m telephony.outbound.agent dev
```

Terminal two, safe validation only:

```bash
uv run python -m telephony.outbound.dial \
  --to YOUR_LINPHONE_USERNAME \
  --district Lucknow \
  --crop tomato \
  --language en \
  --consent-confirmed \
  --dry-run
```

After the dry run succeeds, remove `--dry-run` to call the Linphone app. Use `--language hi` for a Devanagari Hindi opening. Calls require `--consent-confirmed`, are blocked after opt-out, and are limited to 08:00–20:00 IST unless `--override-quiet-hours` is deliberately supplied for a controlled demo.

For the failure-path recording, use `--district "Not a district"` on your own Linphone account. The call still connects, but the live-weather tool reports that current data is unavailable and does not guess. Busy, declined, unanswered, voicemail, and SIP errors are logged and shut down the call worker cleanly.

## Setup

### 1. Install dependencies

```bash
cd backend
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env.local
```

Fill in your keys in `.env.local`:

| Variable             | Where to get it                                           |
| -------------------- | --------------------------------------------------------- |
| `LIVEKIT_URL`        | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_KEY`    | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_SECRET` | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` | LiveKit Cloud → Telephony → SIP Trunks       |
| `MURF_API_KEY`       | [murf.ai/api/dashboard](https://murf.ai/api/dashboard)    |
| `DEEPGRAM_API_KEY`   | [deepgram.com](https://console.deepgram.com/)             |
| `GOOGLE_API_KEY`     | [aistudio.google.com](https://aistudio.google.com/apikey) |

For LiveKit Cloud users, you can auto-populate LiveKit credentials:

```bash
lk cloud auth
lk app env -w -d .env.local
```

### 3. Download models

```bash
uv run python src/agent.py download-files
```

This downloads Silero VAD and the LiveKit turn detector models.

### 4. Run the agent

```bash
# Development mode (auto-reload)
uv run python src/agent.py dev

# Or test directly in your terminal (no frontend needed)
uv run python src/agent.py console

# Production
uv run python src/agent.py start
```

## Configuration

All configuration lives in [`src/agent.py`](src/agent.py).

### System prompt

The `SYSTEM_PROMPT` constant at the top of `agent.py` controls what your agent does. Change it to build any voice-powered use case.

#### Example prompts

**Customer Support (default):**

```
You are a friendly and efficient customer support agent for a tech company. Help users with account issues, billing questions, and product troubleshooting. Be concise, empathetic, and solution-oriented. If you don't know something, say so honestly and offer to escalate.
```

**Language Tutor:**

```
You are a patient and encouraging language tutor helping the user practice conversational Spanish. Speak primarily in Spanish but switch to English to explain grammar or vocabulary when needed. Correct mistakes gently and suggest better phrasing. Keep conversations natural and fun.
```

**AI Receptionist:**

```
You are a professional receptionist for a medical clinic. Help callers schedule appointments, answer questions about office hours and services, and take messages for doctors. Be warm but efficient. Ask for the caller's name and reason for calling upfront.
```

**Interview Coach:**

```
You are an experienced interview coach. Conduct mock interviews with the user for software engineering roles. Ask one behavioral or technical question at a time, let the user answer fully, then give specific feedback on their response — what was strong, what could improve, and a suggested reframe. Keep the tone encouraging but honest.
```

**Sales Assistant:**

```
You are a knowledgeable sales assistant for an electronics store. Help customers find the right product by asking about their needs, budget, and preferences. Compare options clearly, highlight trade-offs, and make a recommendation. Never be pushy — focus on helping the customer make the best decision for them.
```

**Fitness Coach:**

```
You are an upbeat personal fitness coach. Help users plan workouts, suggest exercises for specific muscle groups, and answer questions about form and technique. Ask about their fitness level and any injuries before recommending exercises. Keep instructions clear and motivating.
```

**Storyteller / Bedtime Narrator:**

```
You are a creative storyteller who tells original bedtime stories for children aged 4–8. Ask the child (or parent) for a character name, a favorite animal, and a setting, then weave a short, calming story. Use vivid but simple language. End each story on a peaceful, sleepy note.
```

**Meeting Summarizer:**

```
You are a meeting assistant. The user will describe what happened in a meeting or read you their notes. Summarize the key decisions, action items (with owners if mentioned), and any open questions. Be concise and structured. Ask clarifying questions if something is ambiguous.
```

**Trivia Game Host:**

```
You are an enthusiastic trivia game host. Ask the user one trivia question at a time from a mix of categories — science, history, pop culture, geography, and sports. Wait for their answer, tell them if they're right or wrong, give a brief fun fact, then move to the next question. Keep score and announce it every 5 questions.
```

**Mental Health Check-in Companion:**

```
You are a gentle, non-clinical wellness companion. Help users talk through their day, reflect on how they're feeling, and practice simple grounding exercises like deep breathing or gratitude lists. You are not a therapist — if the user expresses serious distress or mentions self-harm, gently encourage them to reach out to a professional or crisis helpline.
```

### Voice

Set the `voice` argument in the `murf.TTS(...)` call:

```python
tts=murf.TTS(
    voice="en-US-matthew",    # Change this
    style="Conversation",
    tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
    text_pacing=True
)
```

Some voice options:

| Voice ID | Description                      |
| -------- | -------------------------------- |
| `Anisha` | Indian English, female (default) |
| `Amara`  | US English, female               |
| `Hazel`  | UK English, female               |
| `Gordon` | US English, male                 |

Browse all 150+ voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library).

### STT (Speech-to-Text)

Default is Deepgram Nova-3. Change in the `AgentSession(stt=...)` call:

```python
stt=deepgram.STT(model="nova-3")
```

### LLM

Default is Google Gemini. To switch:

- **Gemini (default):** Set `GOOGLE_API_KEY` in `.env.local`
- **OpenAI:** Set `OPENAI_API_KEY`, install `livekit-agents[openai]`, and change the `llm=` argument

## Testing

### Day 7 human-help tool

`src/escalation.py` stores consented help requests in local SQLite at `memory.db`. The `create_escalation` LiveKit tool is limited to serious crop problems and missing or stale market data. It requires both `consent_confirmed=True` and an explicit affirmative in the caller's latest English, Hindi, or Hinglish turn.

Stored summaries contain only useful structured details and never the full transcript. Sensitive passwords, OTPs, PINs, account/card numbers, and long digit sequences are replaced with `[REDACTED]`. Matching active requests reuse their `KS-YYYYMMDD-XXXX` reference. `src/help_requests_cli.py` is the JSON bridge used by the Next.js `/api/help-requests` routes and the `/help-requests` dashboard.

Run the offline Day 7 tests with:

```bash
.venv/bin/python -m pytest \
  tests/test_escalation.py \
  tests/test_db.py \
  tests/test_help_requests_cli.py \
  tests/test_agent.py -q -k "not test_offers_assistance and not test_grounding and not test_refuses_harmful_request"
```

The three excluded tests call external LiveKit inference and require network access. All storage, consent, redaction, duplicate, CLI, and tool behavior tests run locally.

The project includes an eval suite based on the LiveKit Agents [testing framework](https://docs.livekit.io/agents/build/testing/):

```bash
uv run pytest
```

Tests are in [`tests/test_agent.py`](tests/test_agent.py) and use LLM-as-judge evaluations to verify the agent behaves correctly (friendly greetings, grounding, refusing harmful requests).

To run tests in CI, you'll need to add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` as repository secrets.

## Deployment

### Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1?referralCode=cNjn2P&utm_medium=integration&utm_source=template&utm_campaign=generic)

Set these environment variables in Railway:

- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY`
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

### Docker

A production-ready [Dockerfile](Dockerfile) is included:

```bash
docker build -t murf-voice-agent .
docker run --env-file .env.local murf-voice-agent
```

## Project Structure

```
backend/
├── src/
│   └── agent.py          # Agent entrypoint — pipeline, prompt, config
├── tests/
│   └── test_agent.py     # LLM-judged eval suite
├── .env.example           # Environment variable template
├── pyproject.toml         # Python dependencies (uv)
├── Dockerfile             # Production container
└── railway.toml           # Railway deploy config
```

## Links

- [Murf Falcon TTS Docs](https://murf.ai/api/docs/text-to-speech/streaming)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Agents Docs](https://docs.livekit.io/agents)
- [Deepgram Nova-3 Docs](https://developers.deepgram.com)

## License

MIT — see [LICENSE](LICENSE).
