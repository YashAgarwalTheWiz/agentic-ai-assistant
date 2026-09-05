import os
import re
from openai import OpenAI, BadRequestError
from dotenv import load_dotenv

from state import AgentState
from nodes.tools.registry import TOOL_SCHEMAS

load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get('GROQ_API_KEY'),
)
MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')

CITATION_RE = re.compile(r'【[^】]*】')

NUDGE = {
    "role": "user",
    "content": (
        "That tool does not exist. Use only the tools provided in this request, "
        "or answer directly from the results you already have."
    ),
}


def _content(response) -> str:
    """Model text with gpt-oss citation markers stripped."""
    return CITATION_RE.sub('', response.choices[0].message.content or '').strip()


def _to_assistant(response) -> dict:
    """Convert an SDK message into a plain, JSON-serialisable dict."""
    msg = response.choices[0].message
    assistant_msg = {"role": "assistant", "content": _content(response)}
    if msg.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return assistant_msg


def _complete(messages):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )


def llm_call(state: AgentState) -> dict:
    """Ask the model what to do next.

    It either answers (content, no tool_calls) or requests one or more tools.
    We do not decide for it -- that is the entire point of the loop.
    """
    try:
        response = _complete(state['messages'])
    except BadRequestError as e:
        if 'tool_use_failed' not in str(e):
            raise
        # Model hallucinated a tool (gpt-oss reaching for its built-in
        # browser). Tell it so and give it one more attempt.
        response = _complete(state['messages'] + [NUDGE])
        return {
            "messages": [NUDGE, _to_assistant(response)],
            "response": _content(response),
        }

    return {
        "messages": [_to_assistant(response)],
        "response": _content(response),
    }