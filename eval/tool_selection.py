"""Phase 4, part 1 -- tool-selection eval.

Checks whether the agent picks the right tool (or no tool) for a set of
seed prompts. Calls the REAL model (and, for search/RAG cases, real
external services) -- a single run isn't a reliable measurement, which
is why each case runs several times and we report a rate, not a verdict.

NOTE on the search_documents cases: they assume a PDF relevant to their
phrasing is already uploaded (currently written against test3.pdf, a
paper on fine-tuning a sports-image CNN with dropout). If no matching
PDF is present, those two cases will fail for a reason that has nothing
to do with the model's tool-picking judgment -- a real fragility of any
RAG eval, not a bug here.

Costs real Groq API calls -- N_TRIALS times per case (12 cases here, so
36 calls at N_TRIALS=3; some ambiguous cases search more than once
internally, so the real total can run higher). A 2-second pause between
every call plus automatic retry-with-backoff on rate limits are both
here because a full run genuinely generates enough traffic to hit
Groq's free-tier per-minute token cap partway through -- confirmed by
hitting it in an earlier run of this exact script.

Requires GROQ_API_KEY. Run with:
    python eval/tool_selection.py
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import RateLimitError

import nodes.memory_writer as memory_writer_module
from agent import workflow

# Protect the real long-term memory profile -- see prior discussion in
# this file's history. These prompts are generic and the NONE-detection
# fix should stop garbage from being saved, but this makes it a hard
# guarantee instead of trusting that behaviour in an unattended script.
memory_writer_module.save_long_term_memory = lambda *a, **k: None

N_TRIALS = 3
SECONDS_BETWEEN_CALLS = 2
MAX_RATE_LIMIT_RETRIES = 3

SEED_CASES = [
    # -- no tool: settled facts, small talk, things it should just know
    {"prompt": "hi", "expected": "no_tool"},
    {"prompt": "who won the first IPL ever", "expected": "no_tool"},
    {"prompt": "what is the capital of France", "expected": "no_tool"},
    {"prompt": "explain how photosynthesis works", "expected": "no_tool"},
    {"prompt": "what's 15 times 12", "expected": "no_tool"},
    {"prompt": "thanks, that's helpful", "expected": "no_tool"},

    # -- web_search: current, time-sensitive, or "latest"/"current" phrasing
    {"prompt": "who won IPL 2026", "expected": "web_search"},
    {"prompt": "what's the weather in Mumbai right now", "expected": "web_search"},
    {"prompt": "who is the current prime minister of India", "expected": "web_search"},
    {"prompt": "what's the latest iPhone model", "expected": "web_search"},

    # -- search_documents: depends on test3.pdf already being uploaded
    {"prompt": "according to the uploaded paper, what fine-tuning strategy "
               "was used for the sports classifier",
     "expected": "search_documents"},
    {"prompt": "what does my document say about the dropout rate used during training",
     "expected": "search_documents"},
]


def requested_tools(result):
    """Every tool name the model asked for in this run -- gated,
    cancelled, or executed, it doesn't matter here. We're only checking
    what it *chose*, not whether it ran."""
    names = []
    for m in result.get("messages", []):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            names.extend(c["function"]["name"] for c in m["tool_calls"])
    return names


def run_case(prompt):
    chat_id = f"eval-{uuid.uuid4()}"
    thread_id = f"{chat_id}:{uuid.uuid4()}"

    initial_state = {
        "messages": [],
        "chat_id": chat_id,
        "thread_id": thread_id,
        "user_input": prompt,
        "long_term_memory": "",
        "response": "",
        "steps": 0,
        "executed_tools": [],
    }

    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            result = workflow.invoke(
                initial_state, config={"configurable": {"thread_id": thread_id}}
            )
            return requested_tools(result)
        except RateLimitError:
            wait = 5 * (attempt + 1)
            print(f"    (rate limited, waiting {wait}s...)")
            time.sleep(wait)

    print("    (still rate limited after retries, skipping this trial)")
    return []


def matches_expectation(requested, expected):
    if expected == "no_tool":
        return requested == []
    return expected in requested


def main():
    total_passed = 0
    total_trials = 0

    for case in SEED_CASES:
        case_passed = 0
        print(f'\n"{case["prompt"]}"  (expected: {case["expected"]})')

        for trial in range(1, N_TRIALS + 1):
            requested = run_case(case["prompt"])
            ok = matches_expectation(requested, case["expected"])
            case_passed += ok
            mark = "PASS" if ok else "FAIL"
            print(f"  trial {trial}: [{mark}] got {requested or 'no_tool'}")
            time.sleep(SECONDS_BETWEEN_CALLS)

        total_passed += case_passed
        total_trials += N_TRIALS
        print(f"  -> {case_passed}/{N_TRIALS} trials passed")

    print(f"\nOverall: {total_passed}/{total_trials} trials passed "
          f"({100 * total_passed // total_trials}%)")


if __name__ == "__main__":
    main()