"""Deterministic test: a tool that raises must never crash tool_node.

Unlike eval/, this never calls the real model or the real internet -- it
hands tool_node a hand-built state requesting a tool we've deliberately
broken, and checks _run()'s exception handling holds regardless of what
the tool itself throws. This is why it lives in tests/, not eval/: the
same broken tool produces the same result every single time.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nodes.tool_node as tn
from nodes.tools.registry import TOOLS


def state_with(tool, args, call_id="call_1"):
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
        "thread_id": "test-thread",
        "steps": 0,
    }


def test_a_throwing_read_tool_never_crashes_tool_node(monkeypatch):
    """web_search is a read tool -- it never reaches interrupt() at all,
    so this checks _run()'s try/except in isolation."""

    def exploding_tool(query):
        raise RuntimeError("simulated network failure")

    monkeypatch.setitem(TOOLS, "web_search", exploding_tool)

    # Must not raise -- if it does, this test fails with a real traceback.
    out = tn.tool_node(state_with("web_search", {"query": "anything"}))

    result_message = out["messages"][0]["content"]
    assert "Error running web_search" in result_message
    assert "RuntimeError" in result_message
    assert "simulated network failure" in result_message


def test_wrong_arguments_return_a_clean_error_not_a_crash(monkeypatch):
    """Calling a real tool with an argument name it doesn't accept
    produces a TypeError -- caught the same way, one branch up."""

    def picky_tool(expected_arg_name_that_does_not_match):
        return "should never get here"

    monkeypatch.setitem(TOOLS, "web_search", picky_tool)

    out = tn.tool_node(state_with("web_search", {"query": "anything"}))

    result_message = out["messages"][0]["content"]
    assert "Error: wrong arguments for web_search" in result_message