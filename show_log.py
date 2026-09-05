"""Print the approval audit log."""

import json
from memory.approvals import get_approvals

rows = get_approvals()

if not rows:
    print("No approval events yet. Save a note and approve it.")

for r in rows:
    event_id, chat_id, thread_id, call_id, tool, args, decision, ts = r
    try:
        pretty = json.dumps(json.loads(args))[:70]
    except (json.JSONDecodeError, TypeError):
        pretty = str(args)[:70]
    print(f"{ts[:19]}  {decision:<10} {tool:<12} {pretty}")

approved = sum(1 for r in rows if r[6] == 'approved')
cancelled = sum(1 for r in rows if r[6] == 'cancelled')
print(f"\n{approved} approved, {cancelled} cancelled, {len(rows)} total")