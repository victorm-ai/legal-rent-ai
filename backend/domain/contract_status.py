"""Contract lifecycle status values and transition rules (RF-56)."""

from domain.entities import Role

VALID_STATUSES = frozenset(
    {
        "draft",
        "in_review",
        "approved",
        "in_signing",
        "signed",
        "expired",
        "terminated",
    }
)

TERMINAL_STATUSES = frozenset({"expired", "terminated"})

LOCKED_STATUSES = frozenset({"terminated"})

# Lawyers only see contracts once the client sends them for legal review (RF-56).
LAWYER_VISIBLE_STATUSES = frozenset(VALID_STATUSES - {"draft"})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"in_review"}),
    "in_review": frozenset({"draft", "approved", "terminated"}),
    "approved": frozenset({"in_signing", "terminated"}),
    "in_signing": frozenset({"signed", "terminated"}),
    "signed": frozenset({"expired", "terminated"}),
    "expired": frozenset({"terminated"}),
    "terminated": frozenset(),
}

ROLE_TRANSITIONS: dict[str, frozenset[tuple[str, str]]] = {
    Role.CLIENT: frozenset(
        {
            ("draft", "in_review"),
            ("in_review", "approved"),
        }
    ),
    Role.LAWYER: frozenset(
        {
            ("approved", "terminated"),
        }
    ),
}


class InvalidStatusTransitionError(Exception):
    """Raised when a contract status change is not allowed."""

    def __init__(self, message: str = "Invalid status transition"):
        super().__init__(message)
        self.message = message


def is_contract_locked(status: str) -> bool:
    return status in LOCKED_STATUSES


def is_visible_to_lawyer(status: str) -> bool:
    """Return True when a contract may be listed or opened by a lawyer."""
    return status in LAWYER_VISIBLE_STATUSES


def validate_status_value(status: str) -> None:
    if status not in VALID_STATUSES:
        raise InvalidStatusTransitionError(f"Unknown status: {status}")


def can_transition(role: str, current_status: str, target_status: str) -> bool:
    """Return True when the role may move a contract between the two statuses."""
    validate_status_value(current_status)
    validate_status_value(target_status)

    if current_status == target_status:
        return True

    if target_status not in ALLOWED_TRANSITIONS.get(current_status, frozenset()):
        return False

    allowed_for_role = ROLE_TRANSITIONS.get(role, frozenset())
    return (current_status, target_status) in allowed_for_role


def assert_transition(role: str, current_status: str, target_status: str) -> None:
    """Raise InvalidStatusTransitionError when the transition is not permitted."""
    if current_status == target_status:
        return

    if not can_transition(role, current_status, target_status):
        raise InvalidStatusTransitionError(
            f"Cannot change status from {current_status} to {target_status}"
        )
