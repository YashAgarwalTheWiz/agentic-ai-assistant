"""save_note -- the first write tool.

Deliberately trivial. Its job is to prove the approval gate works end to
end before anything with an OAuth flow and a public audience goes near it.
Worst case here is a stray markdown file.
"""

import os
import re
from datetime import datetime

from nodes.tools.registry import tool

NOTES_DIR = os.environ.get('NOTES_DIR', 'notes')


def _slug(title: str) -> str:
    """Filesystem-safe stem, capped so long titles don't blow past the
    OS filename limit."""
    s = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return (s or 'note')[:50]


@tool(
    name="save_note",
    description=(
        "Save a note to the user's local notes folder. Use this when the user "
        "explicitly asks you to write something down, save it, or keep it as a "
        "note. Do NOT use it to store facts about the user for your own recall "
        "-- that happens automatically. Do NOT use it to answer a question. "
        "This writes a real file to disk and the user must approve it before "
        "it runs, so only call it when saving is what was asked for."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": (
                    "A short title of 3-8 words describing the note. Becomes "
                    "the filename. Example: 'Groq rate limit findings'."
                ),
            },
            "body": {
                "type": "string",
                "description": (
                    "The full note content in markdown. Write it out properly "
                    "-- this is what gets saved, so do not abbreviate or refer "
                    "back to the conversation."
                ),
            },
        },
        "required": ["title", "body"],
    },
    write=True,
)
def save_note(title: str, body: str) -> str:
    notes_dir = os.environ.get('NOTES_DIR', 'notes')
    os.makedirs(notes_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(notes_dir, f"{stamp}-{_slug(title)}.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n_Saved {datetime.now():%Y-%m-%d %H:%M}_\n\n{body}\n")
    return f"Note saved to {path}"