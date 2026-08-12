"""Pure configuration and safety rules for outbound advisory calls."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from language import ResponseLanguage, detect_response_language

CallLanguage = Literal["en", "hi"]

IST = ZoneInfo("Asia/Kolkata")
LINPHONE_USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
E164_NUMBER = re.compile(r"^\+[1-9]\d{6,14}$")

ENGLISH_OPENING = (
    "Hello, this is Kisan Sahayak calling with a live rain and crop-safety "
    "advisory for your farm. Say “stop calls” at any time and I will opt you "
    "out of future calls."
)
HINDI_OPENING = (
    "नमस्ते, मैं किसान सहायक हूँ और आपके खेत के लिए बारिश तथा फसल-सुरक्षा की "
    "ताज़ा सूचना देने के लिए कॉल कर रही हूँ। भविष्य की कॉल रोकने के लिए कभी भी "
    "“कॉल बंद करें” कहें।"
)


class CallSafetyError(ValueError):
    """Raised when a call request is unsafe or malformed."""


@dataclass(frozen=True)
class OutboundCallMetadata:
    """Validated information passed from the dial CLI to the voice worker."""

    destination: str
    district: str
    language: CallLanguage = "en"
    crop: str | None = None
    consent_confirmed: bool = False
    quiet_hours_override: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "OutboundCallMetadata":
        try:
            payload = json.loads(value)
        except (json.JSONDecodeError, TypeError) as error:
            raise CallSafetyError(
                "Outbound call metadata is not valid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise CallSafetyError("Outbound call metadata must be a JSON object.")

        allowed_fields = {
            "destination",
            "district",
            "language",
            "crop",
            "consent_confirmed",
            "quiet_hours_override",
        }
        if set(payload) - allowed_fields:
            raise CallSafetyError("Outbound call metadata contains unknown fields.")

        destination = payload.get("destination")
        district = payload.get("district")
        language = payload.get("language", "en")
        crop = payload.get("crop")
        consent_confirmed = payload.get("consent_confirmed", False)
        quiet_hours_override = payload.get("quiet_hours_override", False)

        if not isinstance(destination, str) or not isinstance(district, str):
            raise CallSafetyError(
                "Outbound call metadata requires destination and district strings."
            )
        if language not in {"en", "hi"}:
            raise CallSafetyError("Outbound call metadata language must be en or hi.")
        if crop is not None and not isinstance(crop, str):
            raise CallSafetyError("Outbound call metadata crop must be a string.")
        if not isinstance(consent_confirmed, bool) or not isinstance(
            quiet_hours_override, bool
        ):
            raise CallSafetyError(
                "Outbound call metadata safety flags must be boolean."
            )

        return cls(
            destination=destination.strip(),
            district=district.strip(),
            language=language,
            crop=crop.strip() if crop else None,
            consent_confirmed=consent_confirmed,
            quiet_hours_override=quiet_hours_override,
        )


def validate_call_request(
    metadata: OutboundCallMetadata,
    now: datetime | None = None,
) -> None:
    """Reject a call before dispatch when its safety contract is not satisfied."""
    destination = metadata.destination.strip()
    if not (
        LINPHONE_USERNAME.fullmatch(destination) or E164_NUMBER.fullmatch(destination)
    ):
        raise CallSafetyError(
            "Outbound destination must be a Linphone username or E.164 number."
        )
    if not metadata.district.strip():
        raise CallSafetyError("Outbound call district is required for live weather.")
    if metadata.language not in {"en", "hi"}:
        raise CallSafetyError("Outbound call language must be en or hi.")
    if not metadata.consent_confirmed:
        raise CallSafetyError(
            "Recipient consent must be confirmed before an outbound call."
        )

    requested_at = now or datetime.now(IST)
    if requested_at.tzinfo is None or requested_at.utcoffset() is None:
        raise CallSafetyError("Call time must include a timezone.")
    india_time = requested_at.astimezone(IST)
    if not 8 <= india_time.hour < 20 and not metadata.quiet_hours_override:
        raise CallSafetyError(
            "Outbound calls are allowed only between 08:00 and 20:00 IST."
        )


def opening_greeting(language: CallLanguage) -> str:
    """Return the fixed two-sentence identity, reason, and opt-out disclosure."""
    if language == "en":
        return ENGLISH_OPENING
    if language == "hi":
        return HINDI_OPENING
    raise CallSafetyError("Outbound call language must be en or hi.")


def turn_language_instruction(text: str) -> str:
    """Choose English or native-script Hindi from the recipient's latest turn."""
    exact_values = (
        " Preserve every numeric value and timestamp returned by tools exactly."
    )
    if turn_language(text) == "en":
        return (
            "The recipient's latest turn is English. Reply only in English for "
            "this turn, regardless of the opening language." + exact_values
        )
    return (
        "The recipient's latest turn is Hindi or Roman Hindi. Reply only in "
        "Hindi written in Devanagari for this turn; never use romanized Hindi."
        + exact_values
    )


def turn_language(text: str) -> CallLanguage:
    """Map clear English to English and Hindi/Roman Hindi to native Hindi."""
    mode = detect_response_language(text)
    if mode is ResponseLanguage.ENGLISH:
        return "en"
    return "hi"
