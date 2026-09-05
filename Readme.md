# 🤖 Agentic AI Assistant

A tool-calling AI agent with short-term memory, long-term memory, RAG over uploaded PDFs, web search, MCP-sourced tools, and email sending — all gated behind a **human approval gate** for any action that changes the outside world — built with LangGraph, FastAPI, ChromaDB, SQLite, and Streamlit. Includes a growing evaluation suite covering tool-selection accuracy and output quality.

---

## ✨ Features

- **Real agent loop** — the model decides which tools to call and when. `llm_call → tool_node → llm_call` cycles until it stops requesting tools, capped by a step limit.
- **Short-term memory** — per-chat history in SQLite, persisted across sessions
- **Long-term memory** — durable user facts maintained as a single running profile per user in ChromaDB, updated (not duplicated) each turn
- **Web search** — DuckDuckGo, called when the model decides it needs current information
- **RAG** — upload a PDF, chunked into ChromaDB; searched only when the user refers to their own uploaded document, not for general knowledge
- **MCP tool sourcing** — connects to remote MCP servers and registers their tools automatically, alongside hand-written ones
- **Send email** — sends a real email via Gmail SMTP; gated like every other write tool
- **Human approval gate** — write tools cannot execute until a human approves. The graph suspends mid-run and resumes on decision. Arguments are editable before approval.
- **Audit trail** — every approval and cancellation recorded to SQLite _before_ the tool runs
- **Deterministic safety tests** — gate fail-closed behaviour, tool-error handling, and PDF-upload error handling, all in `tests/`
- **Model-driven evaluation** — tool-selection accuracy and output-quality checks (faithfulness, relevancy) against seed cases, in `eval/`

---

## 🏗️ Architecture

```

Streamlit (UI)
↓ HTTP
FastAPI (Backend)
↓
LangGraph Agent (SqliteSaver checkpointer)

START
↓
memory_retrieval SQLite history + ChromaDB facts + system prompt
↓
llm_call ←────────┐ model answers, or requests tools
↓ │
[tool_calls?] │
├── yes ──→ tool_node ──┘ read tools run immediately
│ write tools → interrupt() → wait for human
└── no ──→ memory_writer → END

```

---

## 🔐 The approval gate

Tools declare their own risk class:

```python
@tool(name="save_note", description="...", parameters={...}, write=True)
def save_note(title: str, body: str) -> str:
    ...
```

`write=True` puts the tool in `WRITE_TOOLS`. `tool_node` calls `interrupt()` **before executing anything**, and the graph suspends. Approved calls execute with **whatever arguments came back** — editing before approving changes what actually runs.

**Fail closed.** Anything that isn't an explicit approval for a specific `tool_call_id` is a cancellation. `nodes/approval.py` holds this logic with no langgraph import, so it's unit-testable alone.

### MCP-sourced tools

`nodes/tools/mcp_bridge.py` connects to a remote MCP server at import time and registers each tool it offers through the same `@tool` decorator. Classification does **not** trust the server: a tool is only read-only if `annotations.readOnlyHint` is exactly `True`. Missing annotations default to gated.

### Sending email

`nodes/tools/mailer.py` — `send_email` sends via Gmail SMTP with an app password. A write tool like any other, so every send is gated and logged.

---

## 🧪 Evaluation (Phase 4, in progress)

Split into two kinds, deliberately kept separate:

**`tests/`** — deterministic. Same input, same result, every time. Covers the approval gate's fail-closed behaviour, a tool that throws or is called with wrong arguments, and a scanned PDF with no extractable text returning a clean 400 instead of a 500.

**`eval/`** — calls the real model (and real external services), so a single run isn't a reliable measurement. Each case runs several trials and reports a pass _rate_, not a verdict — a single miss can mean the model's ordinary variance, or a tool description that needs sharper wording, not a bug.

### Tool-selection eval

`eval/tool_selection.py` checks whether the agent picks the right tool — or correctly picks none — across seed cases: settled trivia, small talk, arithmetic, current-events questions, and questions specifically about an uploaded document. Includes automatic retry-with-backoff for transient rate limits, since a full run generates enough real traffic to occasionally hit them.

### Output-quality eval, judged by the app's own model

`eval/groq_judge.py` wraps the project's existing Groq client as a DeepEval-compatible judge model, so evaluation runs on the same free-tier setup as the rest of the app rather than requiring a separate OpenAI key.

DeepEval's metrics need the judge to return valid JSON matching a schema — a real risk with a smaller model, since DeepEval's own docs note this can fail evaluation outright. The wrapper handles it defensively: strips markdown code fences the model may add despite instructions not to (same category of cleanup as the citation-marker regex in `llm_call.py`), and on a failed parse, retries once with a corrective nudge before raising a clear `JudgeOutputError` — rather than a buried DeepEval-internal traceback.

Validated with `eval/judge_stress_test.py` against a nested list-of-objects schema (structurally closer to what real metrics use internally than a flat object) and `FaithfulnessMetric` runs against both a supported and a genuinely contradicted claim — confirming the judge correctly distinguishes "consistent with the given sources" from "contradicts them," not just producing a plausible-sounding number regardless of content.

---

## 📁 Folder structure

```
Agentic-Ai-Assistant/
├── api.py                   # FastAPI: /chat, /resume, /validate_args, /upload_pdf...
├── streamlit_app.py         # Chat UI + approval card
├── agent.py                 # Graph definition + SqliteSaver checkpointer
├── state.py                 # AgentState TypedDict
├── show_log.py              # Print the approval audit log
├── show_ltm.py              # Print current long-term memory
├── nodes/
│   ├── memory_retrieval.py  # History + facts + system prompt
│   ├── llm_call.py          # Model call, tool schemas, gpt-oss workarounds
│   ├── tool_node.py         # Executes tools; gates writes behind interrupt()
│   ├── approval.py          # Pure decision logic (no langgraph import)
│   ├── memory_writer.py     # Saves messages + maintains the long-term profile
│   └── tools/
│       ├── registry.py      # @tool decorator, read/write split, schema lookup
│       ├── search.py        # web_search        (read)
│       ├── rag.py           # search_documents  (read)
│       ├── notes.py         # save_note         (WRITE)
│       ├── mailer.py        # send_email        (WRITE)
│       └── mcp_bridge.py    # remote MCP tools, fail-closed classification
├── memory/
│   ├── short_term.py        # SQLite messages + chats
│   ├── long_term.py         # ChromaDB user profile (one entry per user, upserted)
│   └── approvals.py         # Approval audit log
├── tests/                   # deterministic
│   ├── test_gate.py
│   ├── test_safety.py
│   ├── test_tool_error_handling.py
│   └── test_pdf_upload_errors.py
├── eval/                    # model-driven, results reported as a rate
│   ├── tool_selection.py
│   ├── groq_judge.py
│   ├── judge_scratch.py
│   └── judge_stress_test.py
├── notes/, uploaded_pdfs/, chroma_db/
├── chat_memory.db           # messages, chats, approval_events
└── checkpoints.db           # langgraph checkpoints
```

---

## 🚀 Running it

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`.env`:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
GMAIL_ADDRESS=your_address@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
```

Two terminals:

```bash
uvicorn api:app --reload
streamlit run streamlit_app.py
```

---

## 🔌 API

| Method | Endpoint              | Description                                               |
| ------ | --------------------- | --------------------------------------------------------- |
| GET    | `/chats`              | All chat sessions                                         |
| POST   | `/new_chat`           | Create a chat session                                     |
| POST   | `/chat`               | Send a message; returns a reply **or** a pending approval |
| POST   | `/resume`             | Approve / edit / cancel a pending action                  |
| POST   | `/validate_args`      | Which required arguments are missing                      |
| GET    | `/messages/{chat_id}` | Message history                                           |
| POST   | `/upload_pdf`         | Upload and ingest a PDF                                   |

---

## 🧪 Testing

```bash
pytest tests/ -v                     # deterministic
python eval/tool_selection.py        # tool-selection accuracy
python eval/judge_stress_test.py     # output-quality judge validation
python show_log.py                   # audit trail
python show_ltm.py                   # current long-term memory
```

**Verify the deterministic tests can fail** by flipping the fail-closed default in `tool_node` to `"approved"` — the malformed-payload tests should go red. A safety test never seen failing proves nothing.

---

## 🧪 Development notes

### Gotchas

**One checkpointer thread per turn, not per chat** — `operator.add` on `messages` plus a rebuilt history every turn would double context each turn otherwise.

**A resumed node re-executes from its first line** — parsing is split out (`plan_calls`) so nothing before the gate has side effects.

**`search_documents`'s own description caused it to overreach.** Its original wording explicitly told the model to prefer the tool for "technical or academic questions phrased generally" — which meant a completely unrelated uploaded PDF got searched for questions like "explain photosynthesis," simply because the phrasing sounded academic. Rewritten to trigger only on explicit references to the user's own document ("my document", "the uploaded paper"), with a fallback to answering directly when unsure.

**MCP annotations can't be trusted, and often aren't even sent** — fail closed on absence, not just on an explicit "unsafe" hint.

**A closure built inside a `for` loop captures the loop variable, not its value** — MCP tool registration freezes each tool's name via a real function argument, not a loop-scoped one.

**Long-term memory was duplicating and losing facts** — fixed with a fixed id per user plus `upsert`, and by showing the model its own existing profile so it extends rather than replaces it. The "return NONE" check also needed `in`, not `==` — the model often wraps NONE in a full sentence.

**A successful SMTP send does not mean the message was delivered** — Gmail can accept a message and then silently filter it into spam afterward. No exception is raised in this case.

**DeepEval's default judge is OpenAI, and defaults to expecting strong instruction-following for JSON output.** Using the app's own Groq-hosted model as the judge instead avoids a second provider dependency, but needs defensive handling (code-fence stripping, one corrective retry) to stay reliable — validated separately in `judge_stress_test.py` before relying on it for anything real.

**Eval and tests are deliberately separate folders**, not different naming within one. A test calling the real model isn't testing code — it's measuring behaviour that can legitimately vary run to run, and conflating the two makes a flaky eval look like a broken test.

### Known limitations

- Approve/Cancel is all-or-nothing across multiple pending write calls.
- Tool calls aren't persisted, so the `🔧` caption vanishes on chat reload.
- One MCP server connected (DeepWiki); no allowlist yet, so even its harmless tools are gated by default.
- `send_email` has no delivery confirmation beyond SMTP acceptance.
- Output-quality eval has been validated against reconstructed and stress-test data, not yet against a real captured agent response end-to-end.
- Single hardcoded `default_user`; one Chroma collection shared across all chats.

### Next

Wire the output-quality judge into a real eval file running against actual agent responses. Then an MCP allowlist, followed by LinkedIn as another write tool.

---

## 👤 Author

**Yash Agarwal**
Fresher @ TCS | ML/AI Engineer in progress
[GitHub](https://github.com/YashAgarwalTheWiz)
