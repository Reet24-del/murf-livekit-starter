# Caller Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete privacy-safe, persistent caller memory for Kisan Sahayak.

**Architecture:** `db.py` owns the SQLite schema and profile upsert contract. `agent.py` obtains an authenticated LiveKit identity, exposes lookup/save tools, retrieves the profile when a call begins, and supplies a personalized greeting. Tests exercise the database against a temporary file and validate the agent-facing contract.

**Tech Stack:** Python 3.10+, SQLite, LiveKit Agents, pytest, Ruff.

## Global Constraints

- Store only Farm & Field profile data: name, language preference, crops grown, land size, district, irrigation type, and last interaction.
- Never write a caller profile without an actual LiveKit participant identity.
- Require caller consent before saving newly learned details; a direct request to save is consent.
- Do not commit the local SQLite database.

---

### Task 1: Test and harden persistent profile storage

**Files:**
- Modify: `backend/src/db.py`
- Create: `backend/tests/test_db.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `init_db(db_path: str | None = None) -> None`
- Produces: `get_caller(user_id: str, db_path: str | None = None) -> dict[str, str] | None`
- Produces: `save_caller(..., db_path: str | None = None) -> None`

- [ ] **Step 1: Write failing database tests**

```python
def test_save_caller_preserves_unsupplied_facts(tmp_path):
    db_path = str(tmp_path / "callers.db")
    init_db(db_path)
    save_caller("caller-1", name="Ramesh", crops_grown="cotton", db_path=db_path)
    save_caller("caller-1", district="Wardha", db_path=db_path)
    assert get_caller("caller-1", db_path)["crops_grown"] == "cotton"
```

- [ ] **Step 2: Run the database tests to verify the missing validation fails**

Run: `uv run pytest tests/test_db.py -v`

- [ ] **Step 3: Implement path injection, input validation, and partial-update storage**

```python
def save_caller(user_id: str, *, db_path: str | None = None, ...) -> None:
    if not user_id.strip():
        raise ValueError("A caller identity is required to save a profile.")
```

- [ ] **Step 4: Run the database tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`

### Task 2: Expose identity-safe caller tools and personalized call startup

**Files:**
- Modify: `backend/src/agent.py`
- Modify: `backend/tests/test_agent.py`

**Interfaces:**
- Produces: `Assistant.get_caller_profile(context: RunContext) -> str`
- Produces: `Assistant.save_caller_profile(context: RunContext, ...) -> str`

- [ ] **Step 1: Write failing tests for unknown identity rejection and required consent instructions**

```python
def test_memory_instructions_require_consent():
    assert "ask for clear permission" in SYSTEM_PROMPT.lower()
```

- [ ] **Step 2: Run the targeted tests and observe the expected failure**

Run: `uv run pytest tests/test_agent.py -v`

- [ ] **Step 3: Add an identity helper, lookup tool, strict consent instruction, and a returning-caller greeting**

```python
def _caller_identity(self) -> str | None:
    ...

@function_tool
async def get_caller_profile(self, context: RunContext) -> str:
    ...
```

- [ ] **Step 4: Run agent and database tests**

Run: `uv run pytest tests/test_db.py tests/test_agent.py -v`

### Task 3: Lint and inspect the final change

**Files:**
- Modify: `backend/src/agent.py`, `backend/src/db.py`, `backend/tests/test_db.py`, `backend/tests/test_agent.py`, `.gitignore`

- [ ] **Step 1: Format and lint the backend**

Run: `uv run ruff format src tests && uv run ruff check src tests`

- [ ] **Step 2: Run the complete backend test suite**

Run: `uv run pytest -v`

- [ ] **Step 3: Inspect the final diff**

Run: `git diff --check && git status --short`
