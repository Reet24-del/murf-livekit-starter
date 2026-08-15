---
title: "Building Kisan Sahayak: What 10 Days of Voice Agents Taught Me"
published: false
description: "How I built a multilingual farming voice agent with LiveKit, Deepgram, Gemini, Murf Falcon, memory, live tools, analytics, and specialist handoffs."
tags: voiceai, ai, python, webdev
---

## A farming assistant that listens

A farmer checking leaves in a field may have wet hands, bright sunlight, and limited time for typing through menus. The question may begin in English, move into Hindi, and end in Hinglish. A useful farming assistant needs to follow that conversation naturally and say when it does not know.

That was the starting point for **Kisan Sahayak**, my Farm & Field project for **10 Days of Voice Agents — VoiceForBharat Edition**. It is a browser and phone-based voice assistant for Indian farmers who need quick help with crop care, soil, irrigation, and local weather.

Over ten days, the project grew from a basic voice loop into a small multi-agent system. It can remember a returning caller with permission, fetch live weather, make a controlled outbound advisory call, create a human-help request, record privacy-safe call outcomes, and transfer crop symptoms to a separate specialist.

The voice layer uses the fastest TTS API — **Murf Falcon**. Murf documents Falcon 2 at about 100 ms time-to-first-audio and supports multilingual speech and code switching, which matters for short, conversational replies.

Repository: [github.com/Reet24-del/murf-livekit-starter](https://github.com/Reet24-del/murf-livekit-starter)

## How the system works

A real-time voice agent has four main parts:

- **Speech-to-text (STT)** turns the caller's audio into text. Kisan Sahayak uses Deepgram Nova-3 with multilingual recognition.
- **A large language model (LLM)** interprets the request, follows the safety instructions, chooses tools, and writes the reply. This project uses Google Gemini.
- **Text-to-speech (TTS)** turns that reply back into audio. The main agent uses Murf Falcon with the Anisha voice; the crop specialist uses Samar so the handoff is audible.
- **Real-time transport** carries microphone audio, transcripts, agent state, and generated speech. LiveKit connects the browser or phone call to the Python agent.

The working flow looks like this:

~~~text
Farmer's microphone
        |
        v
LiveKit real-time room
        |
        v
Deepgram STT  --->  latest-turn language detection
        |                         |
        v                         v
Google Gemini  <--- memory / tools / safety rules
        |
        +------ routine request ------> main Kisan Sahayak agent
        |
        +------ crop symptoms --------> Crop Problem Specialist
        |
        v
Murf Falcon TTS
        |
        v
LiveKit streams the spoken answer back

Side services:
Open-Meteo ---> live district weather
SQLite ------> consented memory, help requests, opt-outs, call outcomes
~~~

LiveKit's agent framework manages the streaming voice pipeline and room lifecycle. The website displays whether the agent is connecting, listening, thinking, speaking, or transferring to the specialist.

## The features that mattered most

### 1. English, Hindi, and Hinglish that follow the caller

Language support is more than multilingual transcription. The answer must match the latest turn.

Kisan Sahayak applies three rules:

- An English turn gets an English reply.
- A Hindi turn gets Hindi in Devanagari.
- Roman Hindi or mixed English-Hindi gets a Roman-script Hinglish reply.

The latest turn takes priority over the greeting, saved language preference, and earlier messages. This stopped an English question from receiving a Hindi answer simply because the session began with a bilingual welcome.

### 2. Memory only after permission

The agent stores a returning caller's useful farming profile in SQLite: name, district, crops, land size, irrigation type, preferred language, and a short conversation summary.

It asks before saving new information. A direct request such as “remember my district” counts as permission. When the caller asks what the agent remembers, it reads the saved record instead of reconstructing a memory from the LLM's context.

This distinction matters:

- Chat context helps during the current call.
- Stored memory helps during a later call.

### 3. Live data through tools

Current information should come from a current source. The weather tool calls Open-Meteo's geocoding and forecast APIs for an Indian district. Its result includes the source timestamp, current conditions, wind, today's temperature range, and rain probability.

If Open-Meteo times out or returns incomplete data, the agent says that live data is unavailable. It does not fill the silence with a guessed temperature.

The current-time question uses a separate tool that reads the system clock in the Asia/Kolkata timezone:

~~~python
@function_tool
async def get_current_india_time(self, context: RunContext) -> str:
    """Use whenever the caller asks for India's current time or date."""
    current_time = format_india_time(datetime.now(INDIA_TIMEZONE))
    return f"The current time in India is {current_time}."
~~~

The tool description is part of the behavior. It tells the model exactly when the call is required and removes the option to guess.

For transparency, weather is live external data. Caller memory, help requests, opt-outs, and analytics are stored in a local SQLite database. The basic crop-suitability lookup is rule-based and should not be mistaken for a live agronomy service.

### 4. A consented path to human help

Kisan Sahayak creates a human-help request for two cases: serious crop damage and missing or stale market data.

It first explains the small set of details it wants to share, then waits for a clear yes or no. Only a confirmed request is written to the database. The saved summary is short, sensitive number patterns are redacted, and the caller receives a reference ID with an honest next step.

The website has a human request log for open, in-progress, and resolved items. It does not display full transcripts, passwords, OTPs, PINs, or account details.

### 5. Call outcomes from real sessions

For this project, a successful call means the farmer received farming guidance, live weather, an outbound rain advisory, or a confirmed expert request. A failed call means the success condition was not reached, even if the software itself did not crash.

Every ended browser or SIP session writes one controlled record with:

- start and end time
- duration
- browser or SIP channel
- detected language
- successful or failed outcome
- one controlled result or failure category

The analytics page calculates total, successful, and failed calls from those SQLite records. It also shows trend and recent-call views without caller identity or transcripts.

### 6. A real specialist handoff

Routine questions stay with the main agent. Reports of leaf spots, pests, wilting, disease, nutrient deficiency, or unexplained crop damage go to a separate **Crop Problem Specialist**.

Before switching, the main agent says that it is connecting the caller. The browser changes to “Connecting you to the specialist,” and then the specialist introduces itself in a different Murf voice. A copy of the existing conversation context is passed across, so the farmer does not need to repeat the symptoms.

The specialist has a narrower job and stricter limits. It gives low-risk first steps, asks one focused question at a time, and does not claim a certain diagnosis from a voice description.

## Three problems that taught me the most

### The response language kept drifting

My first prompt described a bilingual agent, but the bilingual greeting and conversation history often outweighed the caller's latest sentence. English questions sometimes received Hindi answers.

The fix was to detect language on every completed user turn and add a turn-specific instruction. I also separated Devanagari Hindi from Roman-script Hinglish. Tests now cover English, Hindi, and mixed turns instead of checking only the first reply.

**Lesson:** language choice is session state, not a one-time configuration.

### “Current” values were being inferred

The model once gave the wrong current time. The prompt knew about India, but that did not give it a live clock. Weather has the same risk.

I moved both cases behind tools. The time tool reads Asia/Kolkata directly, while the weather tool returns source timestamps and has an eight-second timeout. Failure produces a spoken fallback.

**Lesson:** if a value changes with time, fetch or compute it at the moment of the request.

### Specialist routing competed with human escalation

When the handoff was first added, a crop symptom could trigger the older human-help path. The caller was asked about creating a request instead of being transferred to the specialist. In another run, specialist UI signalling tried to access the local LiveKit participant before the room had connected, and the agent failed to join.

I gave crop symptoms deterministic priority, removed the escalation tool from that initial turn, and resolved the local participant only when the handoff signal is sent after connection. The handoff also sends explicit data packets to the frontend, so the display does not depend on matching transcript phrases.

**Lesson:** multi-agent routing needs explicit ownership rules, and room-dependent work must respect the connection lifecycle.

## Run Kisan Sahayak locally

### Prerequisites

- Python 3.10 to 3.14
- Node.js 20 or newer
- [uv](https://docs.astral.sh/uv/)
- pnpm 9
- accounts and API keys for LiveKit Cloud, Murf, Deepgram, and Google AI

### 1. Clone and install

~~~bash
git clone https://github.com/Reet24-del/murf-livekit-starter.git
cd murf-livekit-starter

cd backend
uv sync
uv run python src/agent.py download-files

cd ../frontend
pnpm install
cd ..
~~~

### 2. Add environment variables safely

~~~bash
cp backend/.env.example backend/.env.local
cp frontend/.env.example frontend/.env.local
~~~

Fill the backend file with:

~~~dotenv
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
MURF_API_KEY=
DEEPGRAM_API_KEY=
GOOGLE_API_KEY=
~~~

The frontend file needs the same LiveKit project and the browser agent name:

~~~dotenv
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
AGENT_NAME=kisan-sahayak-primary
~~~

Keep both `.env.local` files on your machine. They are ignored by Git. Never paste real keys, SIP trunk IDs, phone destinations, caller records, or `backend/memory.db` into a post or commit.

### 3. Start both services

On macOS or Linux:

~~~bash
chmod +x start_app.sh
./start_app.sh
~~~

Open [http://localhost:3001](http://localhost:3001), select **Start Call**, and allow microphone access. The backend and frontend must use the same LiveKit Cloud project and agent name.

### 4. Test both routes

Ask a normal question:

> What is today's weather in Lucknow?

Then start another call and ask:

> My tomato leaves have black spots and are curling.

The first should stay with Kisan Sahayak and call the weather tool. The second should announce a transfer, change the website state, and continue with the Crop Problem Specialist.

End each call, then open [http://localhost:3001/call-analytics](http://localhost:3001/call-analytics). The total should increase, and the outcome should reflect whether the call reached its success condition.

Outbound calling is a separate optional setup because it requires a provider-owned SIP or phone configuration and consent from the destination.

## How I tested it

The backend suite covers language routing, consent, memory, live-tool failure, analytics classification, outbound safety, and specialist handoff. The frontend unit tests cover analytics query state, audio settings, and specialist UI state. I also test the real browser flow because microphone permission, LiveKit connection order, generated speech, and disconnect behavior cannot be proven by isolated unit tests alone.

A useful manual test set is:

1. English question and English answer.
2. Devanagari Hindi question and Hindi answer.
3. Roman Hinglish question and Hinglish answer.
4. Live-weather success and forced failure.
5. Save memory with consent, reconnect, and recall it.
6. Serious issue with consent denied, then consent approved.
7. Normal question that stays with the main agent.
8. Crop symptom that moves to the specialist.
9. End both a completed and an incomplete call and inspect analytics.

## What I would build next

The local SQLite design is good for a single-machine demonstration. A deployed version needs authenticated users, encrypted hosted storage, access controls for the human-help dashboard, and retention rules.

I would also add an agronomist-reviewed knowledge source, district-level mandi data from a dependable source, photo-assisted crop triage, and measured end-to-end latency across different networks. Any crop diagnosis or chemical recommendation should remain bounded by expert-reviewed safety rules.

## Build links

- [Kisan Sahayak source code](https://github.com/Reet24-del/murf-livekit-starter)
- [Murf Falcon 2 documentation](https://murf.ai/api/docs/text-to-speech-models/falcon-2)
- [LiveKit Voice AI quickstart](https://docs.livekit.io/agents/start/voice-ai/)
- [Open-Meteo API documentation](https://open-meteo.com/en/docs)

Kisan Sahayak began as a speaking demo. The ten-day build made the harder requirements visible: fresh data, explicit consent, persistent state, measurable outcomes, and clear agent boundaries. The repository is public for anyone who wants to run the same test questions and build a voice workflow for their own users.

<!--
BEFORE PUBLISHING:
1. Commit and push the current Day 7–10 work, then confirm the public repository
   contains the analytics and specialist-handoff code linked in this article.
2. Add a cover image or a screenshot of the Kisan Sahayak call screen.
   Suggested alt text: "Kisan Sahayak browser voice interface showing the agent listening."
3. Add a screenshot of /call-analytics after one successful test call.
   Suggested alt text: "Privacy-safe call analytics dashboard with total, successful, and failed calls."
4. Preview the article on mobile and verify that no secret or caller data appears.
5. Change published: false to published: true when ready to publish on DEV.
6. Copy the public blog URL into DAY10_LINKEDIN.md.
-->
