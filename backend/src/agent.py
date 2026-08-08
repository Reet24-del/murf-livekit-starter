import asyncio
import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    UserStateChangedEvent,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Structured prompt for Kisan Sahayak Voice Assistant
SYSTEM_PROMPT = """
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
  - If the user speaks to you in Hindi or Hinglish, you MUST reply strictly in Hindi using Devanagari script (Hindi characters, e.g. नमस्कार, टमाटर, मिट्टी). Never write Hindi or Hinglish words using Roman/English letters (do NOT write "Namaskar" or "tamatar").
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
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool
    async def check_crop_suitability(
        self,
        context: RunContext,
        crop_name: str,
    ) -> str:
        """Use this tool to check if a specific crop is suitable for the farmer's current location.
        The tool will automatically detect the location from the farmer's session details.

        Args:
            crop_name: The name of the crop to check (e.g. rice, wheat, tomato).
        """
        location = "Unknown"
        if hasattr(self, "room") and self.room:
            participants = list(self.room.remote_participants.values())
            if participants:
                p = participants[0]
                location = p.attributes.get("location") or "Unknown"
                if location == "Unknown" and p.metadata:
                    try:
                        import json

                        meta = json.loads(p.metadata)
                        location = meta.get("location") or "Unknown"
                    except Exception:
                        pass

        logger.info(f"Checking suitability of {crop_name} for location {location}")

        # Basic climate and soil suitability details in India
        loc_lower = location.lower()
        suitability = ""

        if "bihar" in loc_lower or "patna" in loc_lower:
            if any(x in crop_name.lower() for x in ["rice", "dhan", "धान", "paddy"]):
                suitability = (
                    "धान (rice) के लिए दक्षिण बिहार की जलोढ़ मिट्टी और मौसम बहुत अनुकूल है।"
                )
            elif any(x in crop_name.lower() for x in ["wheat", "gehun", "गेहूं"]):
                suitability = (
                    "गेहूं (wheat) रबी सीजन (अक्टूबर-मार्च) में लगाने के लिए बहुत उपयुक्त है।"
                )
            elif any(x in crop_name.lower() for x in ["maize", "makka", "मक्का"]):
                suitability = (
                    "मक्का (maize) यहाँ खरीफ और रबी दोनों मौसमों में अच्छी उपज देता है।"
                )
            else:
                suitability = f"{crop_name} की खेती की जा सकती है, लेकिन बुवाई से पहले मिट्टी की जांच जरूर कराएं।"
        elif "uttar pradesh" in loc_lower or "lucknow" in loc_lower:
            if any(x in crop_name.lower() for x in ["sugarcane", "ganna", "गन्ना"]):
                suitability = "गन्ना (sugarcane) के लिए उत्तर प्रदेश की मिट्टी और सिंचाई व्यवस्था सर्वोत्तम है।"
            elif any(x in crop_name.lower() for x in ["wheat", "gehun", "गेहूं"]):
                suitability = "गेहूं (wheat) की बुवाई नवंबर में करना सबसे उपयुक्त रहेगा।"
            else:
                suitability = f"{crop_name} की खेती के लिए स्थानीय बुवाई कैलेंडर का पालन करें।"
        else:
            suitability = (
                f"{crop_name} की खेती के लिए मौसम अनुकूल है, बशर्ते समय पर सिंचाई की जाए।"
            )

        return f"स्थान (Location): {location}। रिपोर्ट: {suitability}"

    @function_tool
    async def get_current_weather(
        self,
        context: RunContext,
    ) -> str:
        """Use this tool to get the current weather conditions for the farmer's location.
        The tool automatically detects the location from the session details.
        """
        location = "Unknown"
        if hasattr(self, "room") and self.room:
            participants = list(self.room.remote_participants.values())
            if participants:
                p = participants[0]
                location = p.attributes.get("location") or "Unknown"

        logger.info(f"Looking up weather for location {location}")

        try:
            import aiohttp

            city = location.split(",")[0].strip()
            geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"

            async with aiohttp.ClientSession() as session:
                async with session.get(geocode_url) as resp:
                    geo_data = await resp.json()

                if geo_data.get("results"):
                    result = geo_data["results"][0]
                    lat = result["latitude"]
                    lon = result["longitude"]

                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true"
                    async with session.get(weather_url) as resp2:
                        w_data = await resp2.json()

                    if w_data.get("current_weather"):
                        cw = w_data["current_weather"]
                        temp = cw["temperature"]
                        wind = cw["windspeed"]
                        codes = {
                            0: "Clear sky",
                            1: "Mainly clear",
                            2: "Partly cloudy",
                            3: "Overcast",
                            45: "Foggy",
                            48: "Foggy",
                            51: "Drizzle",
                            53: "Drizzle",
                            55: "Drizzle",
                            61: "Light rain",
                            63: "Rain",
                            65: "Heavy rain",
                            71: "Snow",
                            73: "Snow",
                            75: "Heavy snow",
                            80: "Rain showers",
                            81: "Rain showers",
                            82: "Heavy showers",
                            95: "Thunderstorm",
                        }
                        desc = codes.get(cw["weathercode"], "Clear sky")
                        return f"Current weather in {location}: {temp}°C, {desc}. Windspeed is {wind} km/h."
        except Exception as e:
            logger.error(f"Weather lookup failed: {e}")

        return f"Unable to fetch real-time weather. Typical weather in {location} is 28°C and partly cloudy."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="hi-IN-sunaina",
            locale="hi-IN",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        # Timeout user state to 'away' after 15 seconds of complete silence
        user_away_timeout=15.0,
    )

    silence_failures = 0
    silence_tasks = set()

    @session.on("user_state_changed")
    def on_user_state_changed(ev: UserStateChangedEvent):
        nonlocal silence_failures
        logger.info(f"User state changed: {ev.old_state} -> {ev.new_state}")
        if ev.new_state == "away":
            silence_failures += 1
            if silence_failures == 1:
                logger.info("First silence timeout. Speaking re-prompt.")

                async def re_prompt():
                    try:
                        await session.say(
                            "जी, क्या आप वहाँ हैं? खेती से जुड़ा कोई सवाल है तो पूछिए।"
                        )
                    except Exception as e:
                        logger.error(f"Error speaking re-prompt: {e}")

                t1 = asyncio.create_task(re_prompt())
                silence_tasks.add(t1)
                t1.add_done_callback(silence_tasks.discard)
            elif silence_failures >= 2:
                logger.info(
                    "Second silence timeout. Speaking departure and disconnecting."
                )

                async def close_session():
                    try:
                        await session.say(
                            "आपकी तरफ से कोई जवाब नहीं मिला। मैं कॉल बंद कर रही हूँ। धन्यवाद।"
                        )
                        await asyncio.sleep(4.5)
                        await ctx.disconnect()
                    except Exception as e:
                        logger.error(f"Error during graceful close: {e}")
                        await ctx.disconnect()

                t2 = asyncio.create_task(close_session())
                silence_tasks.add(t2)
                t2.add_done_callback(silence_tasks.discard)
        elif ev.new_state == "speaking":
            # Reset failures if user speaks
            silence_failures = 0

    # Start the session, which initializes the voice pipeline and warms up the models
    assistant = Assistant()
    assistant.room = ctx.room

    await session.start(
        agent=assistant,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()

    # Speak the initial greeting
    await session.say(
        "नमस्कार! मैं आपकी किसान सहायक हूँ। मैं आपको फसल प्रबंधन, मिट्टी की सेहत, और मौसम की जानकारी दे सकती हूँ। आज मैं आपकी क्या सहायता करूँ?"
    )


if __name__ == "__main__":
    cli.run_app(server)
