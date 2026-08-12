"""LiveKit worker that places consented outbound farm-advisory calls."""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import init_db, is_outbound_opted_out, record_outbound_opt_out
from telephony.outbound.call_config import (
    CallLanguage,
    CallSafetyError,
    OutboundCallMetadata,
    opening_greeting,
    turn_language,
    turn_language_instruction,
    validate_call_request,
)
from weather import WeatherLookupError, WeatherReport, fetch_district_weather

logger = logging.getLogger("outbound-agent")

load_dotenv(".env.local")

OUTBOUND_TRUNK_ID = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "")
CALLEE_IDENTITY = "phone-user"

SYSTEM_PROMPT = """
IDENTITY AND PURPOSE:
You are Kisan Sahayak, a female agricultural voice assistant from the Krishi Sahayata Center. This is an outbound call to deliver a live rain and crop-safety advisory. The fixed opening has already identified you, explained why you called, and explained how to stop future calls.

CALL BEHAVIOR:
- Keep every spoken response to one or two short sentences with no markdown, symbols, or lists.
- Call get_live_weather before stating any current condition, temperature, wind, or rain probability.
- Speak the live result naturally and always say when the data was observed or forecast.
- If live data is unavailable, say so clearly and never guess a weather value.
- If the recipient says stop, unsubscribe, do not call, stop calls, कॉल बंद करें, or otherwise asks not to receive future calls, immediately call stop_future_calls.
- If you detect voicemail or an answering machine, immediately call detected_answering_machine.
- When the conversation is complete or the recipient asks to hang up, call end_call.
- Answer only agriculture, crop, and local-weather questions. For complex matters, recommend the Kisan Call Center at 1800-180-1551 or the local KVK.

LANGUAGE & SCRIPT:
- The recipient's latest turn controls the response language.
- English must be written and spoken in English.
- Hindi must always be written in Devanagari. Never write romanized Hindi.
- Treat Roman Hindi as Hindi and answer it in Devanagari.
- Preserve every numeric value and timestamp returned by tools exactly.
- When speaking Hindi, use feminine verb endings such as "कर रही हूँ" and "सकती हूँ".
"""


def metadata_from_job(
    ctx: JobContext,
    *,
    now: datetime | None = None,
    opted_out_lookup: Callable[[str], bool] = is_outbound_opted_out,
) -> OutboundCallMetadata:
    """Parse and revalidate dispatch metadata before any SIP request."""
    raw_metadata = ctx.job.metadata
    if not raw_metadata:
        raise CallSafetyError("Outbound call metadata is required.")
    metadata = OutboundCallMetadata.from_json(raw_metadata)
    validate_call_request(metadata, now=now)
    if opted_out_lookup(metadata.destination):
        raise CallSafetyError(
            "This outbound destination has opted out of future calls."
        )
    return metadata


async def create_outbound_participant(
    ctx: JobContext,
    metadata: OutboundCallMetadata,
    trunk_id: str,
) -> None:
    """Ask LiveKit SIP to call the validated destination and wait for answer."""
    if not trunk_id.strip():
        raise CallSafetyError(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not configured for outbound calls."
        )
    await ctx.api.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            room_name=ctx.room.name,
            sip_trunk_id=trunk_id,
            sip_call_to=metadata.destination,
            participant_identity=CALLEE_IDENTITY,
            participant_name="Farmer",
            wait_until_answered=True,
        )
    )


class OutboundFarmAgent(Agent):
    """Conversational agent for a single validated outbound advisory call."""

    def __init__(
        self,
        ctx: JobContext,
        metadata: OutboundCallMetadata,
        weather_fetcher: Callable[[str], Awaitable[WeatherReport]] = (
            fetch_district_weather
        ),
        opt_out_recorder: Callable[[str], None] = record_outbound_opt_out,
    ) -> None:
        crop_context = metadata.crop or "not provided"
        super().__init__(
            instructions=(
                SYSTEM_PROMPT
                + "\nCONTROLLED CALL CONTEXT:\n"
                + f"District: {metadata.district}\n"
                + f"Crop: {crop_context}\n"
            )
        )
        self.ctx = ctx
        self.metadata = metadata
        self.response_language: CallLanguage = metadata.language
        self._weather_fetcher = weather_fetcher
        self._opt_out_recorder = opt_out_recorder

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        latest_text = new_message.text_content or ""
        self.response_language = turn_language(latest_text)
        turn_ctx.add_message(
            role="system",
            content=turn_language_instruction(latest_text),
        )

    async def _live_weather_response(self) -> str:
        try:
            report = await self._weather_fetcher(self.metadata.district)
        except WeatherLookupError as error:
            logger.warning(
                "Live weather lookup failed for outbound district %s: %s",
                self.metadata.district,
                error,
            )
        except Exception:
            logger.exception(
                "Unexpected outbound weather failure for %s",
                self.metadata.district,
            )
        else:
            return report.to_spoken_text()

        return (
            "Live weather data is unavailable right now, so I will not guess. "
            "Please check your local weather service before making a farm decision."
        )

    @function_tool
    async def get_live_weather(self, context: RunContext) -> str:
        """Fetch the live Open-Meteo weather and today's rain probability for the call's configured district. Call this before giving the outbound rain advisory or answering any current-weather question. Speak its values naturally and include its observation or forecast time."""
        return await self._live_weather_response()

    def _record_opt_out(self) -> str:
        self._opt_out_recorder(self.metadata.destination)
        if self.response_language == "hi":
            return "भविष्य की कॉल बंद कर दी गई हैं।"
        return "Future calls have been stopped for this destination."

    @function_tool
    async def stop_future_calls(self, context: RunContext) -> str:
        """Persistently stop future outbound calls to this recipient. Use immediately when the recipient says stop, unsubscribe, do not call, stop calls, कॉल बंद करें, or makes any equivalent opt-out request."""
        try:
            confirmation = self._record_opt_out()
        except Exception:
            logger.exception(
                "Could not persist outbound opt-out for %s",
                self.metadata.destination,
            )
            return (
                "The opt-out could not be saved right now. Apologize, do not claim "
                "success, and ask the operator to remove this destination manually."
            )

        await context.session.generate_reply(
            instructions=f"Say exactly this confirmation: {confirmation}"
        )
        await self._hangup()
        return "Opt-out saved and call ended."

    @function_tool
    async def detected_answering_machine(self, context: RunContext) -> str:
        """End the call without leaving a message when voicemail or an answering machine is detected."""
        logger.info("Answering machine detected; ending outbound call")
        await self._hangup()
        return "Call ended without leaving a voicemail."

    @function_tool
    async def end_call(self, context: RunContext) -> str:
        """End the outbound call after the recipient is finished or asks to hang up."""
        goodbye = (
            "धन्यवाद। आपकी खेती सुरक्षित रहे।"
            if self.response_language == "hi"
            else "Thank you. Take care of your farm."
        )
        await context.session.generate_reply(
            instructions=f"Say exactly this short goodbye: {goodbye}"
        )
        await self._hangup()
        return "Call ended."

    async def _hangup(self) -> None:
        await self.ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=self.ctx.room.name)
        )


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()
    init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="outbound-agent")
async def outbound_agent(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}
    try:
        metadata = metadata_from_job(ctx)
    except CallSafetyError as error:
        logger.error("Outbound call blocked before dialing: %s", error)
        ctx.shutdown()
        return

    await ctx.connect()
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-3.5-flash-lite"),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
    agent = OutboundFarmAgent(ctx, metadata)
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    )
                )
            ),
        )
    )

    logger.info("Dialing consented outbound destination %s", metadata.destination)
    try:
        await create_outbound_participant(ctx, metadata, OUTBOUND_TRUNK_ID)
    except api.TwirpError as error:
        sip_status = error.metadata.get("sip_status") if error.metadata else None
        logger.error(
            "Outbound call was not answered: %s (SIP status: %s)",
            error.message,
            sip_status,
        )
        session_started.cancel()
        ctx.shutdown()
        return
    except Exception:
        logger.exception("Outbound SIP call failed")
        session_started.cancel()
        ctx.shutdown()
        return

    await session_started
    await session.say(
        opening_greeting(metadata.language),
        allow_interruptions=True,
    )
    advisory_instruction = (
        "Call get_live_weather now, then give the live rain advisory in English."
        if metadata.language == "en"
        else (
            "Call get_live_weather now, then give the live rain advisory in Hindi "
            "written only in Devanagari."
        )
    )
    await session.generate_reply(instructions=advisory_instruction)


if __name__ == "__main__":
    cli.run_app(server)
