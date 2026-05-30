"""
status_machine.py
==================
Single source of truth for knowledge_node status transitions.

Every status change in the system (cascade flagging, doctor reviews,
legal holds/releases, expiry) MUST pass through is_valid_transition()
so the graph can never enter an illegal state.

Status meanings:
    ACTIVE           - valid, trusted knowledge
    REVIEW_REQUIRED  - flagged by cascade; awaiting human review
    SUPERSEDED       - replaced by a newer version (TERMINAL - no exit)
    EXPIRED          - validity window passed (can be re-validated)
    LEGAL_HOLD       - frozen for compliance (ADMIN only; restores prev status)
"""

# All legal "from -> set of allowed to" transitions.
# If a (from, to) pair is not listed here, it is INVALID.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "ACTIVE": {"SUPERSEDED", "REVIEW_REQUIRED", "EXPIRED", "LEGAL_HOLD"},
    "REVIEW_REQUIRED": {"ACTIVE", "SUPERSEDED", "EXPIRED"},
    "EXPIRED": {"ACTIVE"},
    "LEGAL_HOLD": {"ACTIVE", "REVIEW_REQUIRED", "EXPIRED", "SUPERSEDED"},
    # SUPERSEDED is intentionally absent -> it is a TERMINAL state.
    "SUPERSEDED": set(),
}

# Transitions that only an ADMIN may perform.
_ADMIN_ONLY = {
    ("ACTIVE", "LEGAL_HOLD"),
    ("REVIEW_REQUIRED", "LEGAL_HOLD"),
    ("EXPIRED", "LEGAL_HOLD"),
    # any release FROM legal hold is admin-only
    ("LEGAL_HOLD", "ACTIVE"),
    ("LEGAL_HOLD", "REVIEW_REQUIRED"),
    ("LEGAL_HOLD", "EXPIRED"),
    ("LEGAL_HOLD", "SUPERSEDED"),
}

VALID_STATUSES = {
    "ACTIVE", "REVIEW_REQUIRED", "SUPERSEDED", "EXPIRED", "LEGAL_HOLD",
}


class InvalidTransitionError(Exception):
    """Raised when a status change violates the state machine rules."""
    pass


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Return True if moving from_status -> to_status is allowed."""
    return to_status in _ALLOWED_TRANSITIONS.get(from_status, set())


def requires_admin(from_status: str, to_status: str) -> bool:
    """Return True if this transition may only be performed by an ADMIN."""
    return (from_status, to_status) in _ADMIN_ONLY


def assert_transition(from_status: str, to_status: str, actor_role: str) -> None:
    """
    Validate a transition or raise InvalidTransitionError.

    Checks three things:
      1. both statuses are real statuses
      2. the transition is allowed by the state machine
      3. if it's an admin-only transition, the actor is an ADMIN
    """
    if from_status not in VALID_STATUSES:
        raise InvalidTransitionError(f"Unknown source status: {from_status}")
    if to_status not in VALID_STATUSES:
        raise InvalidTransitionError(f"Unknown target status: {to_status}")

    if not is_valid_transition(from_status, to_status):
        raise InvalidTransitionError(
            f"Illegal transition {from_status} -> {to_status}. "
            f"(SUPERSEDED is terminal; check allowed transitions.)"
        )

    if requires_admin(from_status, to_status) and actor_role != "ADMIN":
        raise InvalidTransitionError(
            f"Transition {from_status} -> {to_status} requires ADMIN role, "
            f"but actor role is {actor_role}."
        )


if __name__ == "__main__":
    # Quick self-test of the rules
    checks = [
        ("ACTIVE", "REVIEW_REQUIRED", "EDITOR", True),   # cascade flag - ok
        ("REVIEW_REQUIRED", "ACTIVE", "EDITOR", True),   # review confirms - ok
        ("SUPERSEDED", "ACTIVE", "ADMIN", False),        # terminal - blocked
        ("ACTIVE", "LEGAL_HOLD", "EDITOR", False),       # hold by non-admin - blocked
        ("ACTIVE", "LEGAL_HOLD", "ADMIN", True),         # hold by admin - ok
    ]
    for frm, to, role, expected_ok in checks:
        try:
            assert_transition(frm, to, role)
            got_ok = True
            msg = "ALLOWED"
        except InvalidTransitionError as e:
            got_ok = False
            msg = f"BLOCKED ({e})"
        flag = "OK " if got_ok == expected_ok else "FAIL"
        print(f"[{flag}] {frm} -> {to} as {role}: {msg}")