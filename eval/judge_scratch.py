"""Scratch script -- not part of the app. Tests GroqJudge alone, before
wiring it into any real DeepEval metric. Two checks: does plain
generate() work at all, and does schema-constrained generate() actually
produce valid, usable JSON from gpt-oss-120b -- the exact risk we flagged
before building this."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel
from eval.groq_judge import GroqJudge

judge = GroqJudge()

print("=== plain generate(), no schema ===")
print(judge.generate("Say the word 'hello' and nothing else."))


class Verdict(BaseModel):
    score: int
    reason: str


print("\n=== schema-constrained generate() ===")
result = judge.generate(
    "Rate how relevant this answer is to the question, from 1-10.\n"
    "Question: What is the capital of France?\n"
    "Answer: Paris is the capital of France.",
    schema=Verdict,
)
print(f"type: {type(result)}")
print(f"score: {result.score}")
print(f"reason: {result.reason}")