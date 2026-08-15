# Caller Memory Design

## Goal

Make Kisan Sahayak remember consenting Farm & Field callers across agent restarts.

## Data model

SQLite stores one caller record per non-empty LiveKit participant identity. A record contains the caller's name, language preference, crops grown, land size, district, irrigation type, and an ISO-8601 `last_interaction` timestamp. Partial updates preserve every previously stored fact that was not supplied.

## Agent behavior

The assistant has a `get_caller_profile` function tool and a `save_caller_profile` function tool. Both resolve the caller identity from the connected room and reject missing identities rather than creating a shared profile. At session startup, the backend retrieves a profile to produce a returning-caller greeting; the lookup function remains available to the LLM when it needs to refresh profile context during a call.

The assistant asks for clear permission before saving any newly learned fact. It saves only after an affirmative response in the immediately preceding consent exchange. A direct request to save or remember is treated as affirmative permission. A refusal must result in no write.

## Error handling and privacy

Database errors are logged and yield a concise tool error without ending the call. The local SQLite database is excluded from Git. The system stores only Farm & Field profile facts; it does not introduce storage for financial or health data.

## Verification

Unit tests use a temporary SQLite database to prove initialization, partial-update preservation, and identity validation. Agent tests verify the tools are exposed and the instructions require consent before saving. Ruff and the relevant pytest suite are run before completion.
