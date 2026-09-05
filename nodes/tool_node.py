from memory.approvals import record_decision
from state import AgentState
from nodes.tools.registry import TOOLS, is_write_tool, missing_required
from nodes.approval import plan_calls, normalise_decisions, CANCELLED_RESULT
from langgraph.types import interrupt

MAX_RESULT_CHARS = 4000


def _run(name, args):
    """Execute one tool. Errors are RETURNED, never raised."""
    fn = TOOLS.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'. Available: {list(TOOLS)}"
    try:
        return str(fn(**args))
    except TypeError as e:
        return f"Error: wrong arguments for {name}: {e}"
    except Exception as e:
        return f"Error running {name}: {type(e).__name__}: {e}"


def tool_node(state: AgentState) -> dict:
    """Execute whatever the model asked for and hand the results back.

    Write tools do not run here directly. If the model requested any, the
    graph interrupts and waits for a human decision, which arrives on
    resume as the return value of interrupt().

    On resume, langgraph re-runs this node from the first line, so
    everything above interrupt() must be side-effect free.
    """
    last = state['messages'][-1]
    calls = last.get("tool_calls", []) or []

    plan = plan_calls(calls)                     # phase 1: pure

    pending = [p for p in plan
               if p["error"] is None and is_write_tool(p["name"])]

    decisions = {}
    if pending:                                  # phase 2: gate
        answer = interrupt({
            "type": "approval_request",
            "chat_id": state.get("chat_id"),
            "actions": [{"tool_call_id": p["id"],
                         "tool": p["name"],
                         "arguments": p["args"]} for p in pending],
        })
        decisions = normalise_decisions(answer, pending)

    tool_messages = []                           # phase 3: execute
    executed = []
    for p in plan:
        name, args = p["name"], p["args"]

        if p["error"] is not None:
            result = p["error"]

        elif is_write_tool(name):
            verdict = decisions.get(p["id"],
                                    {"decision": "cancelled", "arguments": args})
            args = verdict["arguments"]

            # Record BEFORE executing. If the tool throws, the approval is
            # still on record and the trail matches what was authorised.
            record_decision(
                chat_id=state.get("chat_id"),
                thread_id=state.get("thread_id"),
                tool_call_id=p["id"],
                tool_name=name,
                arguments=args,
                decision=verdict["decision"],
            )

            if verdict["decision"] == "approved":
                gaps = missing_required(name, args)
                if gaps:
                    result = (f"Error: {name} requires {', '.join(gaps)}. "
                              "Nothing was executed. Retry with complete arguments.")
                else:
                    result = _run(name, args)
                    executed.append({"id": p["id"], "name": name})
            else:
                result = CANCELLED_RESULT

        else:
            result = _run(name, args)
            executed.append({"id": p["id"], "name": name})

        print(f"[TOOL] {name}({args}) -> {result[:300]!r}")
        tool_messages.append({
            "role": "tool",
            "tool_call_id": p["id"],
            "name": name,
            "content": result[:MAX_RESULT_CHARS],
        })

    return {
        "messages": tool_messages,
        "executed_tools": executed,
        "steps": state.get("steps", 0) + 1,
    }