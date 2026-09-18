"""Analysis lifecycle status values and transition rules (RF-58)."""

from domain.entities import Role

VALID_STATUSES = frozenset(
    {
        "processing",
        "ai_generated",
        "pending_review",
        "reviewed",
        "approved",
        "failed",
    }
)

REVIEW_WORKFLOW_STATUSES = frozenset(
    {
        "ai_generated",
        "pending_review",
        "reviewed",
        "approved",
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "ai_generated": frozenset({"pending_review"}),
    "pending_review": frozenset({"reviewed"}),
    "reviewed": frozenset({"approved", "pending_review"}),
    "approved": frozenset(),
    "processing": frozenset(),
    "failed": frozenset(),
}

ROLE_TRANSITIONS: dict[str, frozenset[tuple[str, str]]] = {
    Role.CLIENT: frozenset({("ai_generated", "pending_review")}),
    Role.LAWYER: frozenset(
        {
            ("ai_generated", "pending_review"),
            ("pending_review", "reviewed"),
            ("reviewed", "approved"),
            ("reviewed", "pending_review"),
        }
    ),
}


class InvalidAnalysisStatusTransitionError(Exception):
    """Raised when an analysis status change is not allowed."""

    def __init__(self, message: str = "Invalid analysis status transition"):
        super().__init__(message)
        self.message = message


def validate_analysis_status_value(status: str) -> None:
    if status not in VALID_STATUSES:
        raise InvalidAnalysisStatusTransitionError(f"Unknown analysis status: {status}")


def can_transition(role: str, current_status: str, target_status: str) -> bool:
    validate_analysis_status_value(current_status)
    validate_analysis_status_value(target_status)

    if current_status == target_status:
        return True

    if target_status not in ALLOWED_TRANSITIONS.get(current_status, frozenset()):
        return False

    allowed_for_role = ROLE_TRANSITIONS.get(role, frozenset())
    return (current_status, target_status) in allowed_for_role


def assert_transition(role: str, current_status: str, target_status: str) -> None:
    if current_status == target_status:
        return

    if not can_transition(role, current_status, target_status):
        raise InvalidAnalysisStatusTransitionError(
            f"Cannot change analysis status from {current_status} to {target_status}"
        )
