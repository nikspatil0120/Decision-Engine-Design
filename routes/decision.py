from fastapi import APIRouter
from pydantic import BaseModel, Field

from decision_engine import DecisionEngine

router = APIRouter(prefix="/decision", tags=["decision"])

# ---------------------------------------------------------------------------
# In-memory session store — maps session_id → DecisionEngine instance.
# In production this would be backed by Redis or a database.
# ---------------------------------------------------------------------------
sessions: dict[str, DecisionEngine] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class EvaluationInput(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the interview session.")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Answer quality score in the range 0.0–1.0, produced by the AI evaluator.",
    )


class DecisionOutput(BaseModel):
    next_action: str = Field(..., description='"continue" or "end"')
    prev_difficulty: str = Field(..., description="Difficulty level before this answer was evaluated.")
    difficulty: str = Field(..., description="Current difficulty level after adjustment.")
    question_number: int = Field(..., description="1-based index of the question just answered.")
    reason: str = Field(..., description="Human-readable explanation of the decision.")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/next", response_model=DecisionOutput, summary="Get next interview decision")
def next_decision(payload: EvaluationInput) -> DecisionOutput:
    """
    Accepts an evaluated answer score for a session and returns the engine's
    decision: whether to continue or end the session, the updated difficulty
    level, and the reason for the decision.

    A new DecisionEngine is created automatically for unknown session IDs.
    """
    if payload.session_id not in sessions:
        sessions[payload.session_id] = DecisionEngine()

    engine = sessions[payload.session_id]
    result = engine.evaluate(payload.score)

    return DecisionOutput(
        next_action=result["next_action"],
        prev_difficulty=result["prev_difficulty"],
        difficulty=result["difficulty"],
        question_number=result["question_number"],
        reason=result["reason"],
    )
