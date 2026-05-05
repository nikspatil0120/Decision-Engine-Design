from enum import Enum
from typing import Optional


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class NextAction(str, Enum):
    CONTINUE = "continue"
    END = "end"


# Ordered list used for level navigation
_DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]


class DecisionEngine:
    """
    Rule-based decision engine that determines difficulty adjustment and
    session continuation after each evaluated answer.

    State is maintained per instance, so each interview session should
    have its own DecisionEngine.
    """

    def __init__(self, max_questions: int = 10) -> None:
        self.max_questions: int = max_questions
        self.question_count: int = 0
        self.consecutive_low_scores: int = 0
        self.current_difficulty: Difficulty = Difficulty.EASY
        self.score_history: list[float] = []

        # Scoring thresholds — centralised so they're easy to reconfigure
        self.thresholds: dict[str, float] = {
            "increase": 0.70,
            "decrease": 0.40,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, score: float) -> dict:
        """
        Process a single answer score and return the engine's decision.

        Args:
            score: Float in the range 0.0–1.0 representing answer quality.

        Returns:
            dict with keys:
                next_action       (str)  – "continue" or "end"
                difficulty_adjustment (str) – "increase", "decrease", or "maintain"
                difficulty        (str)  – current difficulty after adjustment
                question_number   (int)  – 1-based index of the question just answered
                reason            (str)  – human-readable explanation
        """
        self.question_count += 1
        self.score_history.append(score)
        self._update_low_score_streak(score)

        difficulty_adjustment, prev_difficulty, new_difficulty = self._adjust_difficulty(score)
        stop, stop_reason = self._check_stopping_condition()

        next_action = NextAction.END if stop else NextAction.CONTINUE
        reason = stop_reason if stop else self._get_reason(score, difficulty_adjustment, prev_difficulty, new_difficulty)

        return {
            "next_action": next_action.value,
            "difficulty_adjustment": difficulty_adjustment,
            "prev_difficulty": prev_difficulty,
            "difficulty": self.current_difficulty.value,
            "question_number": self.question_count,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _adjust_difficulty(self, score: float) -> tuple[str, str, str]:
        """
        Apply threshold rules and mutate current_difficulty.
        Returns (adjustment_label, previous_difficulty, new_difficulty).
        """
        previous = self.current_difficulty.value
        if score > self.thresholds["increase"]:
            self._increase()
            return "increase", previous, self.current_difficulty.value
        elif score < self.thresholds["decrease"]:
            self._decrease()
            return "decrease", previous, self.current_difficulty.value
        else:
            return "maintain", previous, self.current_difficulty.value

    def _increase(self) -> None:
        """Move difficulty up one level, capped at Hard."""
        current_index = _DIFFICULTY_ORDER.index(self.current_difficulty)
        next_index = min(current_index + 1, len(_DIFFICULTY_ORDER) - 1)
        self.current_difficulty = _DIFFICULTY_ORDER[next_index]

    def _decrease(self) -> None:
        """Move difficulty down one level, floored at Easy."""
        current_index = _DIFFICULTY_ORDER.index(self.current_difficulty)
        next_index = max(current_index - 1, 0)
        self.current_difficulty = _DIFFICULTY_ORDER[next_index]

    def _check_stopping_condition(self) -> tuple[bool, Optional[str]]:
        """
        Evaluate all stopping conditions in priority order.

        Returns:
            (should_stop: bool, reason: str | None)
        """
        if self.consecutive_low_scores >= 2:
            return True, (
                "Session ended: 2 consecutive scores below 0.40 — "
                "candidate appears to be struggling."
            )
        if self.question_count >= self.max_questions:
            return True, (
                f"Session ended: reached the maximum of {self.max_questions} questions."
            )
        return False, None

    def _update_low_score_streak(self, score: float) -> None:
        """Increment or reset the consecutive-low-score counter."""
        if score < self.thresholds["decrease"]:
            self.consecutive_low_scores += 1
        else:
            self.consecutive_low_scores = 0

    def _get_reason(self, score: float, adjustment: str, prev: str, new: str) -> str:
        """Build a human-readable reason string showing the difficulty transition."""
        if adjustment == "increase":
            if prev == new:
                return (
                    f"Score {score:.2f} exceeds {self.thresholds['increase']} threshold — "
                    f"already at maximum difficulty ({new})."
                )
            return (
                f"Score {score:.2f} exceeds {self.thresholds['increase']} threshold — "
                f"difficulty increased from {prev} to {new}."
            )
        elif adjustment == "decrease":
            if prev == new:
                return (
                    f"Score {score:.2f} is below {self.thresholds['decrease']} threshold — "
                    f"already at minimum difficulty ({new})."
                )
            return (
                f"Score {score:.2f} is below {self.thresholds['decrease']} threshold — "
                f"difficulty decreased from {prev} to {new}."
            )
        else:
            return (
                f"Score {score:.2f} is within the maintenance range "
                f"({self.thresholds['decrease']}–{self.thresholds['increase']}) — "
                f"difficulty remains {new}."
            )
