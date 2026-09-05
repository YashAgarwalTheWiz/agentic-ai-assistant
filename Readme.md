# 🤖 Agentic AI Assistant

A tool-calling AI agent with short-term memory, long-term memory, RAG over uploaded PDFs, web search, and a **human approval gate** on any action that changes the outside world — built with LangGraph, FastAPI, ChromaDB, SQLite, and Streamlit.

---

## ✨ Features

- **Real agent loop** — the model decides which tools to call and when. `llm_call → tool_node → llm_call` cycles until it stops requesting tools, capped by a step limit. Nothing pre-classifies the query.
- **Short-term memory** — per-chat history in SQLite, persisted across sessions
- **Long-term memory** — durable user facts extracted automatically into ChromaDB, retrieved semantically each turn
- **Web search** — DuckDuckGo, called when the model decides it needs current information
- **RAG** — upload a PDF, chunked into ChromaDB; filenames are injected into the system prompt so the model knows what it can search
- **Human approval gate** — write tools cannot execute until a human approves. The graph suspends mid-run and resumes on decision. Arguments are editable before approval.
- **Audit trail** — every approval and cancellation recorded to SQLite _before_ the tool runs
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

The conditional edge out of `llm_call` is what makes this an agent rather than a pipeline.

---

## 🔐 The approval gate

Tools declare their own risk class:

```python
@tool(name="save_note", description="...", parameters={...}, write=True)
def save_note(title: str, body: str) -> str:
    ...
```

`write=True` puts the tool in `WRITE_TOOLS`. When the model requests one, `tool_node` calls `interrupt()` **before executing anything** and the graph suspends. The pending action surfaces through `/chat`:

```json
{
  "status": "pending_approval",
  "thread_id": "chat-abc:9f2e...",
  "actions": [
    {
      "tool_call_id": "call_1",
      "tool": "save_note",
      "arguments": { "title": "...", "body": "..." }
    }
  ]
}
```

The UI renders it with editable arguments plus Approve / Cancel. The decision returns via `POST /resume` on the same `thread_id`. Approved calls execute with **whatever arguments came back** — editing before approving changes what actually runs. Cancelled calls return a message to the model, which responds conversationally rather than crashing.

### Fail closed

Anything that is not an explicit, recognisable approval for a **specific `tool_call_id`** is treated as a cancellation:

| Resume payload                               | Result                        |
| -------------------------------------------- | ----------------------------- |
| `{"call_1": "approve"}`                      | runs (if `call_1` is pending) |
| `{"wrong_id": "approve"}`                    | cancelled                     |
| `{}` / `None` / `[]` / `"garbage"` / `12345` | cancelled                     |
| `{"call_1": "maybe"}`                        | cancelled                     |

`nodes/approval.py` holds this logic and imports no langgraph, so it is unit-testable without a running graph.

### Validation

Required arguments are checked against the tool's own JSON schema in two places: the UI (`/validate_args`, greys out Approve) and `tool_node` (before execution). The server-side check is the one that matters — the UI check is a convenience.

---

## 📁 Folder structure

```
Chatbot/
├── api.py                   # FastAPI: /chat, /resume, /validate_args, /upload_pdf...
├── streamlit_app.py         # Chat UI + approval card
├── agent.py                 # Graph definition + SqliteSaver checkpointer
├── state.py                 # AgentState TypedDict
├── show_log.py              # Print the approval audit log
├── nodes/
│   ├── memory_retrieval.py  # History + facts + system prompt
│   ├── llm_call.py          # Model call, tool schemas, gpt-oss workarounds
│   ├── tool_node.py         # Executes tools; gates writes behind interrupt()
│   ├── approval.py          # Pure decision logic (no langgraph import)
│   ├── memory_writer.py     # Saves messages + extracts durable facts
│   └── tools/
│       ├── registry.py      # @tool decorator, read/write split, schema lookup
│       ├── search.py        # web_search        (read)
│       ├── rag.py           # search_documents  (read)
│       └── notes.py         # save_note         (WRITE)
├── memory/
│   ├── short_term.py        # SQLite messages + chats
│   ├── long_term.py         # ChromaDB user facts
│   └── approvals.py         # Approval audit log
├── tests/
│   ├── test_gate.py         # Gate behaviour, incl. fail-closed cases
│   └── test_safety.py       # Audit log consistency
├── notes/                   # save_note output (auto-created)
├── uploaded_pdfs/
├── chroma_db/
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

`.env` in the project root:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Two terminals:

```bash
uvicorn api:app --reload        # http://127.0.0.1:8000
streamlit run streamlit_app.py  # http://localhost:8501
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

`/chat` and `/resume` return the **same shape**, discriminated by `status` (`complete` or `pending_approval`). Resuming can itself hit another gate, so the client loops on one code path instead of special-casing a second interrupt.

---

## 🧪 Testing

```bash
pytest tests/ -v        # 14 tests
python show_log.py      # print the audit trail
```

The suite covers: cancel writes nothing, approve writes the file, edited arguments are what execute, a mismatched `tool_call_id` writes nothing, five malformed resume payloads each write nothing, and read tools never reach the gate.

**Verify the tests can fail.** Flip the fail-closed default in `tool_node`:

```python
verdict = decisions.get(p["id"], {"decision": "approved", ...})   # wrong on purpose
```

`test_wrong_call_id_writes_nothing` and all five malformed cases should go red. A safety test never seen failing proves nothing.

---

## 🧪 Development notes

Written down because most of these cost real debugging time and none are obvious from the code.

### Phase 1 — routed workflow → tool-calling agent

The original design had a `router` node: an LLM classified each message as `chat` / `search` / `rag` / `structured` and the graph branched to a matching handler. That is a pipeline wearing an agent's clothes — one capability per turn, no recovery when the classification is wrong.

What replaced it:

- `agent.py` cycles `llm_call → tool_node → llm_call` until the model stops requesting tools. `MAX_STEPS = 8` is the circuit breaker.
- `registry.py` holds a `@tool` decorator registering `TOOLS` and `TOOL_SCHEMAS`. Adding a tool is one decorated function plus one import line.
- `tool_node` returns errors **as tool results** and never raises. The model reading `Error: ...` and trying something else is the behaviour that makes this an agent.
- `messages` got an `Annotated[..., operator.add]` reducer so nodes append rather than overwrite.
- `router.py` was deleted. Structured/dataframe output went with it — it was a routing mode, not a tool.

### Phase 3 — the approval gate

- `SqliteSaver` on `workflow.compile()` is what makes suspend/resume possible at all.
- The registry's `write` flag drives `WRITE_TOOLS`; `tool_node` interrupts before executing any of them.
- `save_note` was chosen as the first write tool precisely because it is trivial. The point was to prove the gate, not the tool — a tool with OAuth, token refresh, and remote API errors gives you four suspects when something fails instead of one.

### Gotchas

**One checkpointer thread per _turn_, not per chat.** `messages` uses `operator.add` and `memory_retrieval` rebuilds full history from SQLite every turn. Reusing a `thread_id` across turns means the previous turn's messages survive in the checkpoint and the fresh history is appended on top — context roughly doubles each turn and the model sees every exchange repeatedly. `/chat` mints `f"{chat_id}:{uuid4()}"`. The checkpointer suspends a single turn; SQLite is the conversation store.

**Construct `SqliteSaver` directly, not via `from_conn_string()`.** That helper is a context manager and closes the connection on exit — fine in a script, fatal in a server. `check_same_thread=False` is required too, since FastAPI runs sync handlers in a threadpool.

**A resumed node re-executes from its first line.** Everything above `interrupt()` in `tool_node` runs twice, so nothing above it may have side effects. That is why parsing is split into `plan_calls()` and no tool executes until after the gate.

**`tools_used` must count executions, not messages.** A cancelled call still produces a `role: "tool"` message — it has to, or the next API call errors on the unanswered `tool_call_id`. Counting messages made cancelled writes look like they ran. `executed_tools` is appended only on actual execution.

**Valid JSON is not valid arguments.** `{}` parses fine and sails through the gate, then dies inside the tool on a missing positional argument — and the model retries into the same wall. Required fields are now checked against the tool's own schema before execution.

**`gpt-oss-120b` hallucinates its own browser tools.** It reaches for built-in `open`, `find`, `search` and emits `【N†source】` markers. Four defences, all needed: search results are not numbered; the system prompt states it has no browser; a regex in `llm_call.py` strips the markers; and a `tool_use_failed` error triggers one retry with a nudge.

**Tool descriptions are load-bearing.** Most of Phase 1's debugging was rewriting English, not Python. A "don't use for general knowledge" clause in `search_documents` was stopping it searching an uploaded paper whenever the question was phrased generally — exactly when you want it to. For write tools this matters more: a vague description means the model proposes actions nobody asked for, the gate fires constantly, and approvals become click-through.

**Chroma corrupts its HNSW index on delete-then-reingest in one process.** `delete_collection()` then re-ingesting without a restart leaves `list_documents()` working but queries throwing "Nothing found on disk." Restart between the two.

**`st.file_uploader` returns the file on every rerun.** Unguarded, every chat message re-ingests the PDF. Guarded with an `ingested` set in session state, deterministic chunk IDs, and `upsert`.

**Tests write to real storage unless stopped.** The gate tests call `tool_node` directly, which calls `record_decision` — early runs put synthetic rows in the production audit log with duplicate ids, and the consistency test correctly flagged the contradiction. Both `NOTES_DIR` and `CHAT_DB` are read at call time so tests can redirect them to `tmp_path`, and they must point at _different_ directories or the test database shows up in the notes listing.

### Known limitations

- Approve/Cancel are all-or-nothing when the model proposes several write calls in one message; you cannot approve one and decline another.
- Switching chats in the sidebar clears a pending approval locally, leaving that turn parked in `checkpoints.db` unanswered.
- Only user/assistant text is persisted to SQLite, so the `🔧 tools · steps` caption disappears when a chat is reloaded.
- Orphaned checkpoints accumulate; nothing prunes `checkpoints.db`.
- One Chroma collection shared across all chats — uploaded documents are visible to every conversation.
- Fact extraction fires a synchronous Groq call every turn, adding latency to every response.
- Single hardcoded `default_user` for long-term memory.

### Next

Phase 4 — evaluation: tool selection, trajectory, output quality (LLM-as-judge), RAG metrics via Ragas. Seed cases: `hi` → no tool; `who won IPL 2026` → `web_search`; `who won the first IPL ever` → no tool (settled fact); a generally-phrased technical question answerable by an uploaded PDF → `search_documents`; scanned PDF → clean 400, not a 500; tool throws → graceful message, no crash.

Then LinkedIn as the second write tool: 3-legged OAuth, `w_member_social` scope, `/rest/posts`, `LinkedIn-Version` header, app linked to a Company Page.

---

## 👤 Author

**Yash Agarwal**
Fresher @ TCS | ML/AI Engineer in progress
[GitHub](https://github.com/YashAgarwalTheWiz)
