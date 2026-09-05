"""Integration test for the approval gate.

Calls tool_node directly with a hand-built state, so no model, no network,
no checkpointer. interrupt() is stubbed to return a decision immediately,
simulating the resume.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nodes.tool_node as tn  # noqa: E402


import uuid


def state_with(tool, args, call_id=None):
    call_id = call_id or f"test_{uuid.uuid4()}"
    return {
        "messages": [{
            "role": "assistant",
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": tool, "arguments": json.dumps(args)},
            }],
        }],
        "chat_id": "test-chat",
        "thread_id": f"test-thread-{uuid.uuid4()}",
        "steps": 0,
    }


@pytest.fixture
def notes_dir(tmp_path, monkeypatch):
    notes = tmp_path / 'notes'
    notes.mkdir()
    monkeypatch.setenv('NOTES_DIR', str(notes))
    monkeypatch.setenv('CHAT_DB', str(tmp_path / 'audit.db'))
    from memory.approvals import init_approvals_db
    init_approvals_db()
    return notes


def answer_with(monkeypatch, decision):
    """Stub interrupt() so it returns as if the human already replied."""
    monkeypatch.setattr(tn, 'interrupt', lambda payload: decision)


def test_cancel_writes_nothing(notes_dir, monkeypatch):
    st = state_with("save_note", {"title": "T", "body": "B"})
    cid = st["messages"][0]["tool_calls"][0]["id"]

    answer_with(monkeypatch, {cid: {"decision": "cancel"}})
    out = tn.tool_node(st)

    assert list(notes_dir.iterdir()) == []
    assert out["executed_tools"] == []
    assert "cancelled" in out["messages"][0]["content"].lower()


def test_approve_writes_the_file(notes_dir, monkeypatch):
    st = state_with("save_note", {"title": "T", "body": "B"})
    cid = st["messages"][0]["tool_calls"][0]["id"]

    answer_with(monkeypatch, {cid: {"decision": "approve",
                                    "arguments": {"title": "T", "body": "B"}}})
    out = tn.tool_node(st)

    files = list(notes_dir.iterdir())
    assert len(files) == 1
    assert "B" in files[0].read_text(encoding='utf-8')
    assert out["executed_tools"][0]["name"] == "save_note"



def test_wrong_call_id_writes_nothing(notes_dir, monkeypatch):
    """Fail closed: approval for a different id must not authorise this one."""
    answer_with(monkeypatch, {"some-other-id": {"decision": "approve"}})
    tn.tool_node(state_with("save_note", {"title": "T", "body": "B"}))

    assert list(notes_dir.iterdir()) == []


@pytest.mark.parametrize("junk", [None, [], {}, "garbage", 12345])
def test_malformed_resume_writes_nothing(notes_dir, monkeypatch, junk):
    """No resume payload shape may result in a write."""
    answer_with(monkeypatch, junk)
    tn.tool_node(state_with("save_note", {"title": "T", "body": "B"}))

    assert list(notes_dir.iterdir()) == []


def test_edited_arguments_are_what_execute(notes_dir, monkeypatch):
    st = state_with("save_note", {"title": "T", "body": "ORIGINAL"})
    cid = st["messages"][0]["tool_calls"][0]["id"]

    answer_with(monkeypatch, {cid: {"decision": "approve",
                                    "arguments": {"title": "T",
                                                  "body": "EDITED"}}})
    tn.tool_node(st)

    text = list(notes_dir.iterdir())[0].read_text(encoding='utf-8')
    assert "EDITED" in text and "ORIGINAL" not in text


def test_read_tool_never_interrupts(monkeypatch):
    """A read tool must not reach the gate at all."""
    def explode(payload):
        raise AssertionError("read tool hit the approval gate")
    monkeypatch.setattr(tn, 'interrupt', explode)

    out = tn.tool_node(state_with("web_search", {"query": "test"}))
    assert out["executed_tools"][0]["name"] == "web_search"