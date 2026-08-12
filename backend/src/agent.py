import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    JobProcess,
    RunContext,
    UserStateChangedEvent,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.agents.voice.events import ConversationItemAddedEvent
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import get_caller, init_db, save_caller
from escalation import create_or_update_help_request
from language import detect_response_language, response_language_instruction
from weather import WeatherLookupError, WeatherReport, fetch_district_weather

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

LIVE WEATHER TOOL:
- For current weather, today's rain chance, temperature, wind, or same-day farm planning, call `get_district_weather` automatically before answering.
- Use the district named by the caller. If none is named, the tool can reuse their saved Day 4 district or session location.
- Speak the tool result naturally and include when the data was observed or forecast.
- If the tool says live data is unavailable, say that clearly. Never invent, estimate, or add weather values that the tool did not return.
- The Open-Meteo timestamp is a weather-data timestamp, not the current clock time. Never describe it as "the current time."

CURRENT TIME TOOL:
- Whenever the caller asks for the current time or date in India, call `get_current_india_time` before answering.
- Repeat the exact time returned by the tool without rounding, converting, or guessing.

LANGUAGE:
- The user's latest turn controls the response language and overrides the greeting, conversation history, saved preferences, and tool-output language.
- If the latest turn contains Devanagari text, reply only in Hindi using Devanagari script.
- If the latest turn is clearly English, reply only in English.
- If the latest turn uses Roman Hindi or mixes Roman Hindi and English, reply naturally in Hinglish using Roman script. Do not convert a Hinglish response into Devanagari.
- If a very short turn is ambiguous, mirror the caller's vocabulary and script instead of forcing English or Hindi.
- Never translate, round, or reinterpret numeric values or times returned by a tool.
- Speak in a warm, respectful, and polite register. Always use gender-neutral respectful terms like "जी" (ji) or "आप" (aap). NEVER assume the user's gender and NEVER use masculine terms like "भैया" (bhaiya) or "brother" to address the user.
- GENDER: You are a female assistant speaking in a woman's voice. When speaking in Hindi, always use feminine verb endings and pronouns (e.g., use "सकती हूँ" instead of "सकता हूँ", "बोल रही हूँ" instead of "बोल रहा हूँ", "करूँगी" instead of "करूँगा").

GUARDRAILS:
- Refuse out-of-scope queries in the latest turn's language. English: "I can only help with farming and weather questions." Hindi: "मैं केवल खेती और मौसम से जुड़े सवालों के जवाब दे सकती हूँ।" Hinglish: "Main sirf farming aur weather ke sawaalon mein help kar sakti hoon."
- Never claim to state current live crop market prices as fact. If asked, explain that market rates fluctuate daily and recommend checking local mandis.
- If a query is outside your knowledge limits, give the escalation in the latest turn's language and recommend the Kisan Call Center at 1800-180-1551 or the local KVK.

MEMORY AND SAVING DATA:
- Memory questions are in scope even when they are not phrased as farming questions. If the caller asks what you remember, whether you remember them, or what you discussed previously, always call `get_caller_profile` before answering.
- Use `get_caller_profile` when you need the caller's saved profile during a conversation. Do not assume profile details or a previous discussion that the tool does not return.
- Ask for clear permission before saving any newly learned detail: "क्या मैं आपकी यह जानकारी अगली बार के लिए सुरक्षित रख सकती हूँ?" Save only after the caller clearly agrees in that consent exchange.
- A direct request to remember or save their details or conversation (for example, "इसे याद रखो", "हमारी बातचीत याद रखना", "मेरा नाम रमेश याद रखना", "remember this conversation", or "save my info") is clear permission. Call `save_caller_profile` immediately, then tell the user what was saved.
- When the caller explicitly asks to remember the current conversation, save `conversation_memory` as a short, factual summary of the farming topic and useful advice discussed. Never store an unrelated or sensitive conversation in this field.
- When recalling a previous conversation, describe only `conversation_memory` returned by the tool. If it is empty, clearly say that no previous conversation summary was saved, while mentioning any profile facts that were saved.
- If the caller says no, do not call the save tool and do not save anything.
- The `save_caller_profile` tool allows partial updates. Pass only the fields that need to be updated and leave other arguments blank/None.

HUMAN HELP:
- Offer human help only for a serious crop problem such as severe or rapidly spreading crop damage, or when exact market data is missing or stale. Do not offer it for normal farming, weather, time, or memory questions.
- For a serious crop problem use high urgency. For missing or stale market data use medium urgency.
- First call `create_escalation` with consent_confirmed=false. Speak its returned consent question exactly; it explains what would be shared and asks whether to create an expert help request.
- Wait for the caller's next answer. Ask for explicit permission with a clear yes or no, and never create the request in the same turn as the problem report.
- Do not treat silence, uncertainty, a delayed answer, or an unrelated yes as permission.
- If the caller says no, do not call `create_escalation` and continue with safe self-service guidance.
- Call `create_escalation` only after the caller explicitly agrees in the current consent exchange. After success, speak the returned reference ID and say the request can be followed in the Help Requests dashboard.
- Never promise that a human will respond immediately or within a specific time. If creation fails, say so and recommend the Kisan Call Center at 1800-180-1551 or the local KVK.

STYLE:
- Keep your spoken responses very short (maximum 1 to 2 simple sentences, under 25 words).
- Speak slowly and clearly.
- Never use markdown formatting, bullet points, or list structures in your text output (e.g. no bold text, no asterisks, no dashes, no numbers). Write plain text only.
"""

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

_CONSENT_NEGATIVE_PATTERN = re.compile(
    r"\b(?:no|nope|do\s+not|don'?t|nahi|nahin|mat)\b|(?:नहीं|नही|मत)",
    re.IGNORECASE,
)
_CONSENT_AFFIRMATIVE_PATTERN = re.compile(
    r"\b(?:yes|yes\s+please|haan|han|sure|please\s+do)\b|(?:हाँ|हां)",
    re.IGNORECASE,
)

_ESCALATION_VALUE_ALIASES = {
    "reason": {
        "serious crop problem": "serious_crop_problem",
        "serious_crop_problem": "serious_crop_problem",
        "market data unavailable": "market_data_unavailable",
        "market_data_unavailable": "market_data_unavailable",
    },
    "urgency": {"high": "high", "medium": "medium"},
    "language": {
        "en": "en",
        "english": "en",
        "hi": "hi",
        "hindi": "hi",
        "hinglish": "hinglish",
    },
    "follow_up_method": {
        "in app": "in_app",
        "in_app": "in_app",
        "in-app": "in_app",
    },
}


def _normalize_escalation_value(field: str, value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    return _ESCALATION_VALUE_ALIASES[field].get(normalized, normalized)


def format_india_time(value: datetime) -> str:
    """Format an aware datetime as an exact IST timestamp."""
    local_value = value.astimezone(INDIA_TIMEZONE)
    return local_value.strftime("%I:%M %p IST on %d %B %Y").lstrip("0")


class Assistant(Agent):
    def __init__(
        self,
        instructions: str = SYSTEM_PROMPT,
        profile_lookup: Callable[[str], dict | None] = get_caller,
        weather_fetcher: Callable[[str], Awaitable[WeatherReport]] = (
            fetch_district_weather
        ),
        escalation_creator: Callable[..., dict[str, str]] = (
            create_or_update_help_request
        ),
    ) -> None:
        super().__init__(instructions=instructions)
        self._profile_lookup = profile_lookup
        self._weather_fetcher = weather_fetcher
        self._escalation_creator = escalation_creator
        self._latest_user_text = ""
        self._user_turn_number = 0
        self._pending_escalation_turn: int | None = None
        self._pending_escalation_payload: dict[str, str] | None = None

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        latest_text = new_message.text_content or ""
        self._latest_user_text = latest_text.strip()
        self._user_turn_number += 1
        mode = detect_response_language(latest_text)
        turn_ctx.add_message(
            role="system",
            content=response_language_instruction(mode),
        )

    def _caller_identity(self) -> str | None:
        if not hasattr(self, "room") or not self.room:
            return None

        participants = list(self.room.remote_participants.values())
        if not participants:
            return None

        identity = participants[0].identity.strip()
        return identity if identity and identity != "unknown" else None

    def _latest_turn_has_explicit_consent(self) -> bool:
        latest_text = self._latest_user_text.strip()
        if not latest_text or _CONSENT_NEGATIVE_PATTERN.search(latest_text):
            return False
        return _CONSENT_AFFIRMATIVE_PATTERN.search(latest_text) is not None

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: Literal["serious_crop_problem", "market_data_unavailable"],
        summary: str,
        checks_performed: str,
        urgency: Literal["high", "medium"],
        language: Literal["en", "hi", "hinglish"],
        consent_confirmed: bool,
        follow_up_method: Literal["in_app"] = "in_app",
    ) -> str:
        """Ask permission, then create human help only for a serious crop problem or missing or stale market data. First call with consent_confirmed false to store a pending request and receive the exact consent question. Create it only after the caller explicitly agrees in the immediately following turn by calling again with true. Never include the full conversation, passwords, OTPs, PINs, account numbers, card numbers, or unrelated personal information.

        Args:
            reason: Either serious_crop_problem or market_data_unavailable.
            summary: A short factual description of what happened.
            checks_performed: A short description of what the agent already checked.
            urgency: High for serious crop problems; medium for unavailable market data.
            language: The caller's current language: en, hi, or hinglish.
            consent_confirmed: False when first offering expert help; true only after explicit permission in the immediately following turn.
            follow_up_method: Always in_app for this project.
        """
        if not consent_confirmed:
            if _CONSENT_NEGATIVE_PATTERN.search(self._latest_user_text):
                self._pending_escalation_turn = None
                self._pending_escalation_payload = None
                return "No human-help request was created."

            self._pending_escalation_turn = self._user_turn_number
            self._pending_escalation_payload = {
                "reason": _normalize_escalation_value("reason", reason),
                "summary": summary,
                "checks_performed": checks_performed,
                "urgency": _normalize_escalation_value("urgency", urgency),
                "language": _normalize_escalation_value("language", language),
                "follow_up_method": _normalize_escalation_value(
                    "follow_up_method", follow_up_method
                ),
            }
            return (
                "I would share your caller identity, short problem summary, checks, "
                "urgency, language, and in-app follow-up. Would you like me to create "
                "an expert help request?"
            )

        consent_is_immediate = (
            self._pending_escalation_turn is not None
            and self._pending_escalation_payload is not None
            and self._user_turn_number == self._pending_escalation_turn + 1
        )
        if not consent_is_immediate or not self._latest_turn_has_explicit_consent():
            self._pending_escalation_turn = None
            self._pending_escalation_payload = None
            return (
                "No human-help request was created because explicit consent was not "
                "confirmed."
            )

        pending_payload = self._pending_escalation_payload
        self._pending_escalation_turn = None
        self._pending_escalation_payload = None

        if pending_payload is None:  # pragma: no cover - guarded above
            return "No human-help request was created because consent expired."

        caller_id = self._caller_identity()
        if caller_id is None:
            return (
                "The human-help request could not be created because the caller "
                "identity is unavailable. Please call the Kisan Call Center at "
                "1800-180-1551 or contact your local KVK."
            )

        caller_name = None
        try:
            profile = self._profile_lookup(caller_id)
            if profile:
                saved_name = profile.get("name")
                if saved_name and saved_name != "Unknown":
                    caller_name = saved_name
        except Exception:
            logger.exception(
                "Failed to retrieve the saved name for help request caller %s",
                caller_id,
            )

        try:
            request = self._escalation_creator(
                caller_id=caller_id,
                caller_name=caller_name,
                reason=pending_payload["reason"],
                summary=pending_payload["summary"],
                checks_performed=pending_payload["checks_performed"],
                urgency=pending_payload["urgency"],
                language=pending_payload["language"],
                follow_up_method=pending_payload["follow_up_method"],
                consent_confirmed=True,
            )
        except Exception:
            logger.exception("Failed to create human-help request for %s", caller_id)
            return (
                "The human-help request could not be created right now. Please call "
                "the Kisan Call Center at 1800-180-1551 or contact your local KVK."
            )

        return (
            f"Human-help request {request['reference_id']} is {request['status']}. "
            "The caller can follow its status in the Help Requests dashboard; a "
            "response time is not guaranteed."
        )

    @function_tool
    async def get_caller_profile(self, context: RunContext) -> str:
        """Look up the current caller's saved Farm & Field profile.

        Use this when profile information would make the current response more useful.
        """
        user_id = self._caller_identity()
        if user_id is None:
            return (
                "Caller profile is unavailable because the caller identity is missing."
            )

        try:
            profile = get_caller(user_id)
        except Exception:
            logger.exception("Failed to look up profile for user_id %s", user_id)
            return "Caller profile could not be retrieved right now."

        if profile is None:
            return "No saved caller profile was found."

        return (
            "Saved caller profile: "
            f"name={profile['name']}; "
            f"language_preference={profile['language_preference']}; "
            f"crops_grown={profile['crops_grown']}; "
            f"land_size={profile['land_size']}; "
            f"district={profile['district']}; "
            f"irrigation_type={profile['irrigation_type']}; "
            f"conversation_memory={profile.get('conversation_memory') or 'not saved'}; "
            f"last_interaction={profile['last_interaction']}."
        )

    @function_tool
    async def save_caller_profile(
        self,
        context: RunContext,
        name: str | None = None,
        crops_grown: str | None = None,
        land_size: str | None = None,
        district: str | None = None,
        irrigation_type: str | None = None,
        language_preference: str | None = None,
        conversation_memory: str | None = None,
    ) -> str:
        """Save or update the farmer's consented profile or conversation memory. Pass only fields that need updating. When the user explicitly asks to remember the current conversation, set conversation_memory to a short summary of the farming topic and advice. Always ask permission first unless the user directly requested saving or remembering.

        Args:
            name: The farmer's name.
            crops_grown: The crops grown by the farmer.
            land_size: The farm land size.
            district: Farmer's district or region.
            irrigation_type: Source of water.
            language_preference: Preferred language of communication.
            conversation_memory: A short summary of a farming conversation the caller explicitly asked to remember.
        """
        user_id = self._caller_identity()
        if user_id is None:
            return (
                "Caller profile was not saved because the caller identity is missing."
            )

        try:
            save_caller(
                user_id=user_id,
                name=name,
                language_preference=language_preference,
                crops_grown=crops_grown,
                land_size=land_size,
                district=district,
                irrigation_type=irrigation_type,
                conversation_memory=conversation_memory,
            )
            logger.info("Successfully saved profile for user_id %s", user_id)
            return "Successfully saved caller profile details in database."
        except Exception:
            logger.exception("Failed to save caller profile for user_id %s", user_id)
            return "Caller profile could not be saved right now."

    def _weather_location(self, district: str | None = None) -> str | None:
        if district and district.strip():
            return district.strip()

        user_id = self._caller_identity()
        if user_id is not None:
            try:
                profile = self._profile_lookup(user_id)
            except Exception:
                logger.exception(
                    "Failed to retrieve saved district for user_id %s", user_id
                )
            else:
                saved_district = profile.get("district") if profile else None
                if saved_district and saved_district != "Unknown":
                    return saved_district.strip()

        if not hasattr(self, "room") or not self.room:
            return None

        participants = list(self.room.remote_participants.values())
        if not participants:
            return None

        participant = participants[0]
        location = participant.attributes.get("location")
        if location and location.strip():
            return location.strip()

        if participant.metadata:
            try:
                import json

                metadata = json.loads(participant.metadata)
            except (TypeError, ValueError):
                return None
            metadata_location = metadata.get("location")
            if metadata_location and metadata_location.strip():
                return metadata_location.strip()

        return None

    async def _district_weather_response(self, district: str) -> str:
        try:
            report = await self._weather_fetcher(district)
        except WeatherLookupError as error:
            logger.warning("Live weather lookup failed for %s: %s", district, error)
            return (
                "Live weather data is unavailable right now, so I will not guess. "
                "Please try again shortly or check your local weather service."
            )
        except Exception:
            logger.exception("Unexpected live weather failure for %s", district)
            return (
                "Live weather data is unavailable right now, so I will not guess. "
                "Please try again shortly or check your local weather service."
            )

        return report.to_spoken_text()

    @function_tool
    async def get_district_weather(
        self,
        context: RunContext,
        district: str | None = None,
    ) -> str:
        """Call this tool whenever a farmer asks about current weather, today's rain chance, temperature, wind, or same-day farm planning such as sowing, spraying, irrigation, or harvesting. Pass the district if the farmer names one; otherwise omit it so the tool can use their saved district.

        Args:
            district: Indian district or city to check. Omit when the caller did not name one.
        """
        location = self._weather_location(district)
        if location is None:
            return "Please tell me your district so I can check live weather."
        return await self._district_weather_response(location)

    @function_tool
    async def get_current_india_time(self, context: RunContext) -> str:
        """Call this tool whenever the caller asks for the current time or current date in India. It reads the live system clock in the Asia/Kolkata timezone, and the answer must repeat the returned time exactly without rounding."""
        current_time = format_india_time(datetime.now(INDIA_TIMEZONE))
        return f"The current time in India is {current_time}."

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


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    init_db()


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
            voice="Anisha",
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
        preemptive_generation=False,
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

    # Track the last user query and log it with the assistant's response to the frontend
    last_user_query = None

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        nonlocal last_user_query
        item = event.item
        role = getattr(item, "role", None)
        text = (
            getattr(item, "text_content", None)
            or getattr(item, "text", None)
            or getattr(item, "content", None)
        )

        if not role or not text:
            return

        if role == "user":
            last_user_query = text
            logger.info(f"Logged user query: {text}")
        elif role == "assistant" and last_user_query:
            logger.info(
                f"Logging complete turn to frontend: Q='{last_user_query}', A='{text}'"
            )
            from datetime import datetime

            import requests

            payload = {
                "user_id": user_id,
                "query": last_user_query,
                "response": text,
                "timestamp": datetime.now().isoformat(),
            }

            def post_query():
                try:
                    res = requests.post(
                        "http://localhost:3001/api/queries", json=payload, timeout=2.0
                    )
                    if res.status_code != 200:
                        logger.warning(
                            f"Failed to log query to frontend, status code: {res.status_code}"
                        )
                except Exception as ex:
                    logger.error(f"Error logging query to frontend API: {ex}")

            asyncio.get_event_loop().run_in_executor(None, post_query)
            last_user_query = None

    # Join the room and connect to the user
    await ctx.connect()

    # Wait a short moment to retrieve remote participant details
    user_id = "unknown"
    for _ in range(10):
        participants = list(ctx.room.remote_participants.values())
        if participants:
            user_id = participants[0].identity
            break
        await asyncio.sleep(0.1)

    logger.info(f"Connected participant identity (User ID): {user_id}")

    # Query caller profile from SQLite database
    profile = None
    if user_id != "unknown":
        try:
            profile = get_caller(user_id)
        except Exception as e:
            logger.error(f"Error querying database for caller profile: {e}")

    # Build dynamic prompt instructions and initial greeting
    if profile:
        name = profile.get("name")
        crops = profile.get("crops_grown") or "फसलें"
        district = profile.get("district") or "क्षेत्र"
        land = profile.get("land_size") or "भूमि"
        irrigation = profile.get("irrigation_type") or "सिंचाई"
        conversation_memory = profile.get("conversation_memory") or "Not saved"

        await assistant.update_instructions(
            SYSTEM_PROMPT
            + f"""

RETURNING USER PROFILE MEMORY:
You are talking to a returning user who is a farmer. Address them warmly and refer to these details:
- Name of caller: {name}
- Crops grown: {crops}
- Farm size: {land}
- District/Location: {district}
- Irrigation Source: {irrigation}
- Saved conversation memory: {conversation_memory}

Use these details only when relevant. If asked about a previous conversation, report only the saved conversation memory and never invent missing details.
"""
        )
        if name and name != "Unknown":
            greeting = (
                f"Welcome back, {name}. फिर से स्वागत है, {name} जी। "
                "You may speak in English or Hindi. आप अंग्रेज़ी या हिंदी में बात कर सकते हैं।"
            )
        else:
            greeting = (
                "Welcome back! फिर से स्वागत है! You may speak in English or Hindi. "
                "आप अंग्रेज़ी या हिंदी में बात कर सकते हैं।"
            )
    else:
        greeting = (
            "Hello! नमस्कार! I am Kisan Sahayak. You may ask your farming or "
            "weather question in English or Hindi. आप अंग्रेज़ी या हिंदी में पूछ सकते हैं।"
        )

    # Speak the initial greeting
    await session.say(greeting)


if __name__ == "__main__":
    cli.run_app(server)
