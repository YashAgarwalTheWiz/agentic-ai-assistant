import json


def plan_calls(calls):
    """Parse tool calls into a plan without executing anything."""
    plan = []
    for call in calls or []:
        name = call.get("function", {}).get("name", "<missing>")
        raw = call.get("function", {}).get("arguments") or "{}"
        entry = {"id": call.get("id"), "name": name, "args": {}, "error": None}
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                entry["error"] = f"Error: arguments for {name} must be a JSON object."
            else:
                entry["args"] = parsed
        except json.JSONDecodeError:
            entry["error"] = (
                f"Error: arguments for {name} were not valid JSON. "
                "Retry with valid JSON."
            )
        plan.append(entry)
    return plan

APPROVE_WORDS = {'approve', 'approved', 'yes', 'y', 'ok', 'confirm', 'accept'}

CANCELLED_RESULT = (
    "Action cancelled by the user. Do not retry this tool call. "
    "Acknowledge the cancellation and ask what they would like instead."
)


def _one(value, original_args):
    if isinstance(value, str):
        approved = value.strip().lower() in APPROVE_WORDS
        return {"decision": "approved" if approved else "cancelled",
                "arguments": original_args}
    if isinstance(value, dict):
        raw = value.get("decision", value.get("action", ""))
        approved = str(raw).strip().lower() in APPROVE_WORDS
        args = value.get("arguments")
        return {"decision": "approved" if approved else "cancelled",
                "arguments": args if isinstance(args, dict) else original_args}
    return {"decision": "cancelled", "arguments": original_args}


def normalise_decisions(resume, pending):
    originals = {p["id"]: p["args"] for p in pending}
    ids = list(originals)

    if isinstance(resume, str):
        return {i: _one(resume, originals[i]) for i in ids}

    if isinstance(resume, dict):
        if ('decision' in resume or 'action' in resume) and not any(i in resume for i in ids):
            return {i: _one(resume, originals[i]) for i in ids}
        return {
            i: _one(resume[i], originals[i]) if i in resume
            else {"decision": "cancelled", "arguments": originals[i]}
            for i in ids
        }

    return {i: {"decision": "cancelled", "arguments": originals[i]} for i in ids}