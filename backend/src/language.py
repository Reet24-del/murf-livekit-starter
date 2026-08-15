import re
from enum import Enum


class ResponseLanguage(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"
    MIRROR = "mirror"


ROMAN_HINDI_MARKERS = frozenset(
    {
        "aaj",
        "aap",
        "aur",
        "baarish",
        "bata",
        "batao",
        "chahiye",
        "fasal",
        "hai",
        "hain",
        "hoga",
        "hogi",
        "ka",
        "kaisa",
        "kaise",
        "kaisi",
        "kal",
        "karna",
        "karo",
        "ke",
        "kheti",
        "ki",
        "ko",
        "main",
        "mausam",
        "mein",
        "mera",
        "mere",
        "meri",
        "mujhe",
        "nahi",
        "paani",
        "pani",
        "rakho",
        "se",
        "tum",
        "yaad",
    }
)

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


def response_language_instruction(mode: ResponseLanguage) -> str:
    return _INSTRUCTIONS[mode]
