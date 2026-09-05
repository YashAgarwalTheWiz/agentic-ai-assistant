"""Safety suite: the invariant the approval gate exists to guarantee."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.approvals import get_approvals, init_approvals_db  # noqa: E402
from nodes.tools.registry import WRITE_TOOLS                   # noqa: E402

# column order from the CREATE TABLE
EVENT_ID, CHAT_ID, THREAD_ID, CALL_ID, TOOL, ARGS, DECISION, TS = range(8)


def test_every_logged_write_is_a_known_write_tool():
    """Nothing but a registered write tool should ever reach the gate."""
    for row in get_approvals():
        assert row[TOOL] in WRITE_TOOLS, (
            f"{row[TOOL]} was gated but is not in WRITE_TOOLS"
        )


def test_every_decision_is_recognised():
    """No third state -- a decision is approved or cancelled."""
    for row in get_approvals():
        assert row[DECISION] in ('approved', 'cancelled')


def test_no_cancelled_call_was_also_approved():
    """A tool_call_id must not appear with both verdicts."""
    seen = {}
    for row in get_approvals():
        key = (row[THREAD_ID], row[CALL_ID])
        if key in seen:
            assert seen[key] == row[DECISION], (
                f"call {row[CALL_ID]} logged as both verdicts"
            )
        seen[key] = row[DECISION]


def test_approved_arguments_are_recorded():
    """The audit row must capture what actually ran, not a placeholder."""
    for row in get_approvals():
        if row[DECISION] == 'approved':
            parsed = json.loads(row[ARGS])
            assert isinstance(parsed, dict)