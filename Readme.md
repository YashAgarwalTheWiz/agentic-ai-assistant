# 🤖 Agentic AI Assistant

A tool-calling AI agent with short-term memory, long-term memory, RAG over uploaded PDFs, web search, MCP-sourced tools, and a **human approval gate** on any action that changes the outside world — built with LangGraph, FastAPI, ChromaDB, SQLite, and Streamlit.

---

## ✨ Features

- **Real agent loop** — the model decides which tools to call and when. `llm_call → tool_node → llm_call` cycles until it stops requesting tools, capped by a step limit.
- **Short-term memory** — per-chat history in SQLite, persisted across sessions
- **Long-term memory** — durable user facts maintained as a single running profile per user in ChromaDB, updated (not duplicated) each turn
- **Web search** — DuckDuckGo, called when the model decides it needs current information
- **RAG** — upload a PDF, chunked into ChromaDB; filenames are injected into the system prompt
- **MCP tool sourcing** — connects to remote MCP servers and registers their tools automatically, alongside hand-written ones
- **Human approval gate** — write tools cannot execute until a human approves. The graph suspends mid-run and resumes on decision. Arguments are editable before approval.
- **Audit trail** — every approval and cancellation recorded to SQLite *before* the tool runs
- **Safety test suite** — asserts no malformed or mismatched approval can trigger a write

---

## 🏗️ Architecture

```
Streamlit (UI)
     ↓ HTTP
FastAPI (Backend)
     ↓
LangGraph Agent   (SqliteSaver checkpointer)

   START
     ↓
  memory_retrieval      SQLite history + ChromaDB facts + system prompt
     ↓
  llm_call  ←────────┐  model answers, or requests tools
     ↓               │
  [tool_calls?]      │
     ├── yes ──→ tool_node ──┘   read tools run immediately
     │                            write tools → interrupt() → wait for human
     └── no  ──→ memory_writer → END
```

---

## 🔐 The approval gate

Tools declare their own risk class:

```python
@tool(name="save_note", description="...", parameters={...}, write=True)
def save_note(title: str, body: str) -> str:
    ...
```

`write=True` puts the tool in `WRITE_TOOLS`. `tool_node` calls `interrupt()` **before executing anything**, and the graph suspends. The pending action surfaces through `/chat`; the decision returns via `POST /resume` on the same `thread_id`. Approved calls execute with **whatever arguments came back** — editing before approving changes what actually runs.

**Fail closed.** Anything that isn't an explicit approval for a specific `tool_call_id` is a cancellation — wrong id, `{}`, `None`, garbage, all cancelled. `nodes/approval.py` holds this logic with no langgraph import, so it's unit-testable alone.

**Validation.** Required arguments are checked against the tool's own schema in `tool_node` before execution, catching cases like `{}` that parse as valid JSON but are missing everything the tool needs.

### MCP-sourced tools

`nodes/tools/mcp_bridge.py` connects to a remote MCP server at import time, asks it for its tools, and registers each one through the same `@tool` decorator as a hand-written tool. From `tool_node`'s side, an MCP tool is indistinguishable from `save_note`.

Classification does **not** trust the server: a tool is only read-only if its `annotations.readOnlyHint` is exactly `True`. Missing or absent annotations default to gated. This isn't theoretical — DeepWiki (the connected server, genuinely read-only) sends no annotations at all, so its tools are currently gated purely as a safe default, not because they're actually risky. No allowlist yet to relax that.

---

## 📁 Folder structure

```
Chatbot/
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
│       └── mcp_bridge.py    # remote MCP tools, fail-closed classification
├── memory/
│   ├── short_term.py        # SQLite messages + chats
│   ├── long_term.py         # ChromaDB user profile (one entry per user, upserted)
│   └── approvals.py         # Approval audit log
├── tests/
│   ├── test_gate.py         # Gate behaviour, incl. fail-closed cases
│   └── test_safety.py       # Audit log consistency
├── notes/, uploaded_pdfs/, chroma_db/
├── chat_memory.db           # messages, chats, approval_events
└── checkpoints.db           # langgraph checkpoints
```

---

## 🚀 Running it

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`.env`:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Two terminals:

```bash
uvicorn api:app --reload
streamlit run streamlit_app.py
```

---

## 🔌 API

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/chats` | All chat sessions |
| POST | `/new_chat` | Create a chat session |
| POST | `/chat` | Send a message; returns a reply **or** a pending approval |
| POST | `/resume` | Approve / edit / cancel a pending action |
| POST | `/validate_args` | Which required arguments are missing |
| GET | `/messages/{chat_id}` | Message history |
| POST | `/upload_pdf` | Upload and ingest a PDF |

`/chat` and `/resume` share one response shape, discriminated by `status`.

---

## 🧪 Testing

```bash
pytest tests/ -v        # 14 tests
python show_log.py      # audit trail
python show_ltm.py      # current long-term memory
```

**Verify the tests can fail** by flipping the fail-closed default in `tool_node` to `"approved"` — the malformed-payload tests should go red. A safety test never seen failing proves nothing.

---

## 🧪 Development notes

### Phase 1 → Phase 3

Routed workflow (`router.py`, deleted) replaced by a real tool-calling loop, then by the approval gate: `SqliteSaver` checkpointer, registry `write` flag, `interrupt()` in `tool_node`, `save_note` as the deliberately trivial first write tool.

### Gotchas

**One checkpointer thread per turn, not per chat** — `operator.add` on `messages` plus a rebuilt history every turn would double context each turn otherwise.

**`SqliteSaver` constructed directly**, not via `from_conn_string()` — that's a context manager and closes the connection on exit, fatal in a server.

**A resumed node re-executes from its first line** — parsing is split out (`plan_calls`) so nothing before the gate has side effects.

**`tools_used` counts executions, not tool messages** — a cancelled call still needs a reply message, so counting messages made cancellations look like they'd run.

**Valid JSON isn't valid arguments** — `{}` passes the JSON check and dies inside the tool; required fields are now checked against the schema first.

**Tool descriptions are load-bearing**, especially for write tools — a vague one means the model proposes unwanted actions and the gate becomes click-through.

**MCP annotations can't be trusted, and often aren't even sent** — DeepWiki proved this: a genuinely read-only server, zero annotations. Fail closed on absence, not just on an explicit "unsafe" hint.

**`asyncio.run()` fails inside an already-running event loop** — hit this at MCP registration time under `uvicorn --reload`. Fixed with a helper that checks for a running loop first and falls back to a separate thread if one exists.

**A closure built inside a `for` loop captures the loop variable, not its value** — caught before running: registering MCP tools in a loop needs each tool's name frozen via a real function argument, or every registered tool ends up calling whichever name was left over after the loop finished.

**Long-term memory was duplicating and losing facts** — `collection.add()` with a random id per call meant every turn created a new entry instead of updating one; fixed with a fixed id per user and `upsert`. Separately, each extraction only saw the current turn, so an update about your job would silently erase your name — fixed by showing the model its own existing profile and asking it to preserve and extend it, not replace it.

**The "return NONE" check needs `in`, not `==`** — the model often wraps NONE in a full sentence even when told to answer with just that word; checking for exact equality let garbage sentences through as if they were real facts.

**Chroma corrupts its HNSW index on delete-then-reingest in one process** — restart between the two.

**`st.file_uploader` returns the file on every rerun** — guarded with an `ingested` set, deterministic chunk IDs, and `upsert`.

### Known limitations

- Approve/Cancel is all-or-nothing across multiple pending write calls.
- Switching chats in the sidebar orphans a parked approval in `checkpoints.db`.
- Tool calls aren't persisted, so the `🔧` caption vanishes on chat reload.
- One MCP server connected (DeepWiki); no allowlist yet, so even its harmless tools are gated by default.
- Single hardcoded `default_user`; one Chroma collection shared across all chats.

### Next

An allowlist so verified-safe MCP tools can skip the gate on the developer's own decision, not the server's claim. Then Phase 4 (tool-selection, trajectory, and RAG evaluation) and LinkedIn as the second write tool.

---

## 👤 Author

**Yash Agarwal**
Fresher @ TCS | ML/AI Engineer in progress
[GitHub](https://github.com/YashAgarwalTheWiz)
