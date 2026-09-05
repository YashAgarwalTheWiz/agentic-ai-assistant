"""Harder stress tests for GroqJudge, addressing two ways the first
scratch test was too easy: a trivial flat schema, and an unambiguous
question. Part 1 uses a nested list-of-objects schema, structurally
closer to what DeepEval's real metrics ask for internally. Part 2 wires
up a REAL DeepEval metric (FaithfulnessMetric) against genuinely
contradictory search results captured in an earlier eval run of "who
won IPL 2026" -- real content difficulty, not another invented example.

Costs several real Groq calls (FaithfulnessMetric alone typically makes
3-4 internally: extracting truths, extracting claims, generating
verdicts, generating a reason). If the daily token quota from earlier
hasn't reset yet, this can hit the same rate limit -- that's expected,
not a bug in this script.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from eval.groq_judge import GroqJudge

judge = GroqJudge()


# ---------------------------------------------------------------- part 1
# A nested schema: a LIST of verdict objects, each with its own fields --
# structurally similar to how DeepEval's real metrics ask a judge to
# verdict a list of extracted claims, not just fill in one flat object.

class ClaimVerdict(BaseModel):
    claim: str
    verdict: str  # "true" | "false" | "unsure"
    reason: str


class ClaimVerdicts(BaseModel):
    verdicts: list[ClaimVerdict]


print("=== part 1: nested list-of-objects schema ===")
result = judge.generate(
    "Break this statement into 3 separate factual claims. For each claim, "
    "say whether it is true, false, or unsure, with a one-sentence reason:\n"
    "'The Eiffel Tower is in Paris, was completed in 1889, and is made "
    "primarily of steel.'",
    schema=ClaimVerdicts,
)
print(f"type: {type(result)}")
for v in result.verdicts:
    print(f"  - claim: {v.claim}")
    print(f"    verdict: {v.verdict}  |  reason: {v.reason}")


# ---------------------------------------------------------------- part 2
# A real DeepEval metric, run on genuinely contradictory search results
# from an earlier real eval run -- not an invented example.

print("\n=== part 2: real FaithfulnessMetric on genuinely contradictory sources ===")

retrieval_context = [
    "2026 Indian Premier League final - Wikipedia\nJuly 24, 2026 - The 2026 "
    "Indian Premier League final was a Twenty20 (T20) cricket match played "
    "at the Narendra Modi Stadium in Ahmedabad, India, on 31 May 2026 to "
    "determine the winner of the 2026 Indian Premier League (IPL).",

    "Ipl 2026 Final Match Winner | TikTok\nRCB IPL 2026 Final Winning Moment "
    "— Champions Celebrated The clip captures the decisive, triumphant "
    "moment when Royal Challengers Bangalore secured the IPL 2026 title.",
]

# Reconstructed plausible answer, NOT verbatim-captured agent output --
# our eval script only logged which tool was called that trial, not the
# model's exact final wording. This is what a model plausibly concludes
# reading only these two snippets.
actual_output = "Royal Challengers Bangalore (RCB) won the 2026 IPL."

test_case = LLMTestCase(
    input="Who won IPL 2026?",
    actual_output=actual_output,
    retrieval_context=retrieval_context,
)

metric = FaithfulnessMetric(model=judge, include_reason=True)
metric.measure(test_case)

print(f"Score: {metric.score}")
print(f"Reason: {metric.reason}")

# -------------------------------------------------------------- part 3
# Part 2's "perfect score" turned out to be the correct answer to the
# wrong question -- the TikTok snippet didn't just imply RCB won, it
# stated it outright, so there was nothing to contradict. This part
# fixes that: two sources that genuinely disagree with each other.
#
# NOTE: this content is entirely invented to force a real disagreement
# for testing purposes -- not a claim about who actually won any real
# match.

print("\n=== part 3: FaithfulnessMetric with a REAL contradiction ===")

contradictory_context = [
    "Official tournament records confirm Mumbai Indians defeated Royal "
    "Challengers Bangalore in the final to win the title.",
    "Some unverified social media posts claimed Royal Challengers "
    "Bangalore won instead, but this was never confirmed by any "
    "official source.",
]

contradicted_output = "Royal Challengers Bangalore won the title."

contradiction_case = LLMTestCase(
    input="Who won the title?",
    actual_output=contradicted_output,
    retrieval_context=contradictory_context,
)

metric2 = FaithfulnessMetric(model=judge, include_reason=True)
metric2.measure(contradiction_case)

print(f"Score: {metric2.score}")
print(f"Reason: {metric2.reason}")