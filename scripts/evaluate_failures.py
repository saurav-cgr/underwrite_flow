"""Safe, sanitized case-level failure reporting for the evaluation runner."""


class EvaluationFailure(Exception):
    """One case-level failure, carrying only its safe result-artifact shape."""

    # Record the sanitized failure a caller reports instead of raising raw.
    def __init__(self, case_id: str, stage: str, code: str) -> None:
        super().__init__(f"{case_id}:{stage}:{code}")
        self.detail = sanitized_failure(case_id, stage, code)


# Build the safe failure record the result artifact stores for one case.
def sanitized_failure(case_id: str, stage: str, code: str) -> dict[str, str]:
    return {"case_id": case_id, "stage": stage, "code": code}
