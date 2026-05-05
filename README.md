# Task 6 — Decision Engine

## Overview

The Decision Engine sits between answer evaluation and next-question selection.
After every answer is scored by the AI evaluator, the engine decides:

1. Should difficulty increase, decrease, or stay the same?
2. Should the session continue or end?
3. What is the reason for the decision?

---

## Rule-Based vs AI-Based Approach

### This engine: Rule-Based

The Decision Engine uses deterministic threshold rules to make decisions.
Given the same score and session state, it will always produce the same output.

**Advantages:**
- Fully predictable and auditable — every decision can be traced to a rule.
- Zero latency overhead — no additional model call required.
- Easy to tune: changing a threshold value immediately changes behaviour for all sessions.
- No risk of hallucinated or inconsistent decisions.

**Trade-offs:**
- Cannot adapt to nuanced patterns (e.g., a candidate who scores 0.41 consistently but never improves).
- Thresholds are hand-crafted and may not generalise across all domains or candidate profiles.

### Alternative: AI-Based Decision

An AI-based approach would feed the full score history, question history, and
candidate profile into a language model and ask it to recommend the next action.

**Advantages:**
- Can reason about trends, not just individual scores.
- Can incorporate qualitative signals (e.g., clarity vs depth trade-offs).

**Trade-offs:**
- Adds latency and cost per question.
- Decisions are harder to audit and explain to candidates.
- Requires careful prompt engineering to avoid inconsistency.

### Hybrid (recommended for production)

Use the rule-based engine as the primary decision-maker and invoke an AI
override only when the rules produce a borderline result (e.g., score within
±0.05 of a threshold). This keeps latency low while allowing nuanced handling
of edge cases.

> **Note:** Although the Decision Engine itself is rule-based, it *consumes*
> AI-generated scores. The `score` field it receives is produced by a GPT-based
> evaluator (via `POST /interview/answer`) that assesses correctness, depth,
> and clarity. The engine therefore benefits from AI quality assessment without
> introducing non-determinism into the control flow.

---

## Scoring Thresholds

| Score Range        | Action              | Effect on Difficulty          |
|--------------------|---------------------|-------------------------------|
| > 0.70             | Increase difficulty | Easy → Medium → Hard          |
| 0.40 – 0.70 (incl.)| Maintain difficulty | No change                     |
| < 0.40             | Decrease difficulty | Hard → Medium → Easy          |

Difficulty is bounded: it cannot go above **Hard** or below **Easy**.

---

## Difficulty Levels

| Level  | Enum Value |
|--------|------------|
| Easy   | `Difficulty.EASY`   |
| Medium | `Difficulty.MEDIUM` |
| Hard   | `Difficulty.HARD`   |

---

## Stopping Conditions

The session ends when **any** of the following conditions is met (evaluated
after each answer, in priority order):

1. **Consecutive low scores** — 2 or more consecutive scores below 0.40.
   Indicates the candidate is struggling and continuing would not be productive.

2. **Maximum questions reached** — the session has reached `max_questions`
   (default: 10, configurable via `DecisionEngine(max_questions=N)`).

When a stopping condition is triggered, `next_action` is set to `"end"` and
the `reason` field explains which condition was met.

---

## Next Actions

| Value      | Meaning                                      |
|------------|----------------------------------------------|
| `continue` | Fetch the next question at the new difficulty |
| `end`      | Close the session and return final results    |

---

## Integration Points

### Task 5 — Domain Mapping System
- After the engine returns `next_action: "continue"`, the caller passes
  `result["difficulty"]` to `generate_prompt(difficulty)` to fetch the next
  question from the domain → topic → subtopic hierarchy.

### Task 5 — API Contract (`POST /interview/answer`)
- The evaluation response contains `score`, `correctness`, `depth`, and
  `clarity`. The `score` field (0.0–1.0) is passed directly to
  `DecisionEngine.evaluate(score)`.

### FastAPI Backend
- `routes/decision.py` exposes `POST /decision/next`.
- The router is registered on the main FastAPI `app` instance.
- Session state is held in-memory (`sessions: dict[str, DecisionEngine]`).
  For multi-worker or persistent deployments, replace with a Redis-backed store.

### PostgreSQL
- Score history (`engine.score_history`) and final difficulty can be persisted
  to the database at session end for analytics and candidate reporting.

---

## File Structure

```
main.py                     # FastAPI app entry point — registers routers, health check
decision_engine.py          # Core logic — Difficulty enum, NextAction enum, DecisionEngine class
routes/
  __init__.py
  decision.py               # FastAPI router — POST /decision/next
test_decision_engine.py     # Plain-Python test script
TASK6_DECISION_ENGINE.md    # This document
```

---

## Running the Server

```powershell
C:\Python313\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once running:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/` | Health check |
| `http://localhost:8000/decision/next` | Decision endpoint |
| `http://localhost:8000/docs` | Swagger UI (interactive testing) |
| `http://localhost:8000/redoc` | ReDoc documentation |

---

## Running the Test Script

```powershell
C:\Python313\python.exe test_decision_engine.py
```

Expected output (max_questions=5, scores=[0.8, 0.75, 0.3, 0.2, 0.9]):

```
======================================================================
DecisionEngine Test — max_questions=5
======================================================================
Q1 | Score: 0.80 → Action: continue | Difficulty: Easy → Medium   | Score 0.80 exceeds 0.7 threshold — difficulty increased from Easy to Medium.
Q2 | Score: 0.75 → Action: continue | Difficulty: Medium → Hard   | Score 0.75 exceeds 0.7 threshold — difficulty increased from Medium to Hard.
Q3 | Score: 0.30 → Action: continue | Difficulty: Hard → Medium   | Score 0.30 is below 0.4 threshold — difficulty decreased from Hard to Medium.
Q4 | Score: 0.20 → Action: end      | Difficulty: Medium → Easy   | Session ended: 2 consecutive scores below 0.40 — candidate appears to be struggling.
Q5 | Score: 0.90 → Action: end      | Difficulty: Easy → Medium   | Session ended: reached the maximum of 5 questions.
======================================================================
```

> The `Difficulty` column always shows the full transition (`before → after`) so every row is self-explanatory.
> Q4 triggers the consecutive-low-score stop. Q5 triggers the max-questions stop.
> On `end` rows the transition still reflects the difficulty change that occurred before the session closed.

---

## Testing the API (PowerShell)

> PowerShell's `curl` is an alias for `Invoke-WebRequest` and does not accept `-X`/`-H`/`-d` flags.
> Use `Invoke-RestMethod` instead.

Single request:

```powershell
Invoke-RestMethod -Method POST -Uri http://localhost:8000/decision/next `
  -ContentType "application/json" `
  -Body '{"session_id": "test-1", "score": 0.85}' | Format-List
```

Full sequence (mirrors the test script):

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$scores = @(0.8, 0.75, 0.3, 0.2, 0.9)
$i = 1
foreach ($score in $scores) {
    $body = "{`"session_id`": `"demo`", `"score`": $score}"
    $r = Invoke-RestMethod -Method POST -Uri http://localhost:8000/decision/next -ContentType "application/json" -Body $body
    Write-Host "Q$i | Score: $score -> Action: $($r.next_action) | Difficulty: $($r.difficulty) | $($r.reason)"
    $i++
}
```

> Each `session_id` maintains independent state. Use a different `session_id` to start a fresh session.
