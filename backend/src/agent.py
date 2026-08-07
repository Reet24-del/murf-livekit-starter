import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    UserStateChangedEvent,
    cli,
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
- Mirror the user's language mix (Hinglish, code-mixed Hindi and English, pure Hindi, or pure English).
- Speak in a warm, respectful, and polite register. Use terms like "bhaiya" or "aap" to show respect.

GUARDRAILS:
- Refuse out-of-scope queries (general knowledge, political topics, sports, coding, entertainment) politely: "Main keval kheti aur mausam se jude sawalon ke jawab de sakta hoon."
- Never claim to state current live crop market prices as fact. If asked, explain that market rates fluctuate daily and recommend checking local mandis.
- If a query is outside your knowledge limits, use this escalation path: "Iske liye main aapko Kisan Call Centre ke toll-free number 1800-180-1551 par baat karne ya apne sthaniy Krishi Vigyan Kendra (KVK) officer se sampark karne ki salah dunga."

STYLE:
- Keep your spoken responses very short (maximum 1 to 2 simple sentences, under 25 words).
- Speak slowly and clearly.
- Never use markdown formatting, bullet points, or list structures in your text output (e.g. no bold text, no asterisks, no dashes, no numbers). Write plain text only.
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


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
        stt=deepgram.STT(model="nova-3"),
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
        preemptive_generation=True,
        # Timeout user state to 'away' after 7 seconds of complete silence
        user_away_timeout=7.0,
    )

    silence_failures = 0

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
                            "Bhaiya, kya aap wahan hain? Kheti se juda koi sawal hai toh poonchhiye."
                        )
                    except Exception as e:
                        logger.error(f"Error speaking re-prompt: {e}")

                ctx.proc.loop.create_task(re_prompt())
            elif silence_failures >= 2:
                logger.info(
                    "Second silence timeout. Speaking departure and disconnecting."
                )

                async def close_session():
                    try:
                        await session.say(
                            "Aapki taraf se koi jawab nahi mila. Main call band kar raha hoon. Dhanyawad."
                        )
                        import asyncio

                        await asyncio.sleep(4.5)
                        await ctx.disconnect()
                    except Exception as e:
                        logger.error(f"Error during graceful close: {e}")
                        await ctx.disconnect()

                ctx.proc.loop.create_task(close_session())
        elif ev.new_state == "speaking":
            # Reset failures if user speaks
            silence_failures = 0

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
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
        "Namaskar! Main aapka Kisan Sahayak hoon. Main aapko fasal prabandhan, mitti ki sehat, aur mausam ki jankari de sakta hoon. Aaj main aapki kya sahayata karoon?"
    )


if __name__ == "__main__":
    cli.run_app(server)
