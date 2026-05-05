"""
Manual test script for DecisionEngine.
Run with: python test_decision_engine.py
No external test framework required.
"""

from decision_engine import DecisionEngine


def run_tests() -> None:
    scores = [0.8, 0.75, 0.3, 0.2, 0.9]
    engine = DecisionEngine(max_questions=5)

    print("=" * 70)
    print("DecisionEngine Test — max_questions=5")
    print("=" * 70)

    for score in scores:
        result = engine.evaluate(score)
        n = result["question_number"]
        action = result["next_action"]
        prev = result["prev_difficulty"]
        curr = result["difficulty"]
        reason = result["reason"]

        # Show transition if difficulty changed, otherwise just current level
        if prev != curr:
            diff_display = f"{prev} → {curr}"
        else:
            diff_display = curr

        print(
            f"Q{n} | Score: {score:.2f} → "
            f"Action: {action} | Difficulty: {diff_display} | {reason}"
        )

    print("=" * 70)


if __name__ == "__main__":
    run_tests()
