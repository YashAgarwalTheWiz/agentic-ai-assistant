"""A DeepEval-compatible judge model backed by our existing Groq client.

DeepEval defaults to OpenAI as the judge for its LLM-as-judge metrics.
This wraps our own Groq-hosted model instead, so evaluation stays on the
same free-tier setup as the rest of the app -- at the cost of a real,
documented risk: DeepEval's metrics need the judge to reliably return
valid JSON matching a given schema, and smaller/less capable models can
fail to do that. We handle it the same way llm_call.py already handles
gpt-oss-120b's other quirks: strip likely formatting noise, then retry
once with a corrective nudge before giving up with a clear error.
"""

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from deepeval.models import DeepEvalBaseLLM

load_dotenv()

MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')

_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get('GROQ_API_KEY'),
)


class JudgeOutputError(Exception):
    """Raised when the judge model's output could not be parsed into the
    schema DeepEval asked for, even after one corrective retry. Meant to
    surface clearly instead of a buried DeepEval-internal traceback."""


def _strip_code_fences(text: str) -> str:
    """Models often wrap JSON in ```json ... ``` even when told not to --
    same category of cleanup as the citation-marker regex in llm_call.py."""
    return re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())


def _ask(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


class GroqJudge(DeepEvalBaseLLM):
    """Custom judge model for DeepEval metrics, backed by Groq."""

    def load_model(self):
        return _client

    def get_model_name(self) -> str:
        return f"Groq {MODEL} (custom judge wrapper)"

    def generate(self, prompt: str, schema: type[BaseModel] | None = None):
        if schema is None:
            return _ask(prompt)

        schema_prompt = (
            f"{prompt}\n\n"
            "Respond with ONLY valid JSON matching this exact structure, "
            "with no other text before or after it, and no markdown code "
            f"fences:\n{json.dumps(schema.model_json_schema(), indent=2)}"
        )

        raw = _ask(schema_prompt)
        try:
            return schema.model_validate_json(_strip_code_fences(raw))
        except Exception:
            pass  # fall through to one corrective retry, below

        retry_prompt = (
            f"{schema_prompt}\n\n"
            f"Your previous response was not valid JSON matching that "
            f"structure. Here is what you sent:\n{raw}\n\n"
            "Send ONLY the corrected, valid JSON now, nothing else."
        )
        raw_retry = _ask(retry_prompt)
        try:
            return schema.model_validate_json(_strip_code_fences(raw_retry))
        except Exception as e:
            raise JudgeOutputError(
                f"Groq judge could not produce valid JSON for schema "
                f"{schema.__name__} after one retry. Last raw output:\n{raw_retry}"
            ) from e

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):
        # No real async infra in this project (same call we made for MCP:
        # a sync bridge, not a rewrite) -- just reuse the sync path.
        return self.generate(prompt, schema)