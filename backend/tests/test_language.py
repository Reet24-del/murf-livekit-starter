import pytest

from language import (
    ResponseLanguage,
    detect_response_language,
    response_language_instruction,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("What is today's weather in Lucknow?", ResponseLanguage.ENGLISH),
        ("आज लखनऊ में मौसम कैसा है?", ResponseLanguage.HINDI),
        ("kal baarish hogi kya", ResponseLanguage.HINGLISH),
        ("Aaj weather kaisa hai", ResponseLanguage.HINGLISH),
        ("kal", ResponseLanguage.MIRROR),
    ],
)
def test_detects_latest_turn_language(
    text: str,
    expected: ResponseLanguage,
) -> None:
    """Catch a turn being forced into the wrong response language or script."""
    assert detect_response_language(text) is expected


def test_hinglish_instruction_requires_roman_script_and_exact_values() -> None:
    """Catch Hinglish being converted to Devanagari or tool values being altered."""
    instruction = response_language_instruction(ResponseLanguage.HINGLISH)

    assert "latest turn is Hinglish" in instruction
    assert "Roman script" in instruction
    assert "numeric value and time" in instruction


def test_mirror_instruction_preserves_ambiguous_caller_style() -> None:
    """Catch a short mixed-language turn being arbitrarily forced to English."""
    instruction = response_language_instruction(ResponseLanguage.MIRROR)

    assert "Mirror the caller's vocabulary and script" in instruction
