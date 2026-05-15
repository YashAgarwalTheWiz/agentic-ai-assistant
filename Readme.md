# 🤖 Agentic AI Assistant

A fully agentic AI chatbot with short-term memory, long-term memory, RAG (document Q&A), web search, and structured output — built with LangGraph, FastAPI, ChromaDB, SQLite, and Streamlit.

---

## ✨ Features

- **Agentic Architecture** — LangGraph-powered agent with a multi-node pipeline: memory retrieval → routing → LLM call → memory writing
- **Short-Term Memory** — Per-chat conversation history stored in SQLite, persisted across sessions
- **Long-Term Memory** — Important user facts extracted automatically and stored in ChromaDB for retrieval across chats
- **Smart Router** — LLM-based query classifier that routes each message to the right handler: `chat`, `search`, `rag`, or `structured`
- **Web Search** — Real-time DuckDuckGo search for current information, injected as context into the LLM
- **RAG (PDF Q&A)** — Upload any PDF and ask questions about it; documents are chunked and stored in ChromaDB
- **Structured Output** — Returns JSON arrays rendered as interactive dataframes in the UI
- **FastAPI Backend** — Clean REST API decoupling the agent logic from the UI
- **Streamlit Frontend** — Chat interface with sidebar for chat history, new chat, and PDF upload

---

## 🏗️ Architecture

```
Streamlit (UI)
     ↓ HTTP
FastAPI (Backend)
     ↓
LangGraph Agent
     ↓
Node 1 → memory_retrieval   (SQLite + ChromaDB)
Node 2 → router             (LLM-based classifier)
Node 3 → llm_call           (chat / search / rag / structured)
Node 4 → memory_writer      (saves to SQLite + ChromaDB)
     ↓
Storage:
SQLite   → short-term memory (per chat)
ChromaDB → long-term memory + RAG documents
Local    → uploaded PDFs (uploaded_pdfs/)
```

---

## 📁 Folder Structure

```
agentic-ai-assistant/
├── api.py                   # FastAPI backend
├── streamlit_app.py         # Streamlit frontend
├── agent.py                 # LangGraph graph definition
├── state.py                 # AgentState TypedDict
├── main.py                  # Basic LLM test
├── nodes/
│   ├── memory_retrieval.py  # Fetches short + long term memory
│   ├── router.py            # LLM-based query type classifier
│   ├── llm_call.py          # Core LLM call with tool integration
│   ├── memory_writer.py     # Saves messages + extracts user facts
│   └── tools/
│       ├── search.py        # DuckDuckGo web search
│       └── rag.py           # PDF ingestion + ChromaDB query
├── memory/
│   ├── short_term.py        # SQLite operations
│   └── long_term.py         # ChromaDB operations
├── uploaded_pdfs/           # Uploaded PDFs stored here
├── chroma_db/               # ChromaDB persistent storage (auto-created)
├── chat_memory.db           # SQLite database (auto-created)
├── .env                     # API keys (not committed)
├── .gitignore
└── requirements.txt
```

---

## 🚀 How to Run

### 1. Clone the repository

```bash
git clone https://github.com/YashAgarwalTheWiz/agentic-ai-assistant.git
cd agentic-ai-assistant
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get your free Groq API key at [console.groq.com](https://console.groq.com)

### 5. Run the FastAPI backend

```bash
uvicorn api:app --reload
```

API will be live at `http://127.0.0.1:8000`

### 6. Run the Streamlit frontend

Open a second terminal (with venv activated):

```bash
streamlit run streamlit_app.py
```

UI will open at `http://localhost:8501`

---

## 🔌 API Endpoints

| Method | Endpoint              | Description                       |
| ------ | --------------------- | --------------------------------- |
| GET    | `/chats`              | Get all chat sessions             |
| POST   | `/new_chat`           | Create a new chat session         |
| POST   | `/chat`               | Send a message and get a response |
| GET    | `/messages/{chat_id}` | Get message history for a chat    |
| POST   | `/upload_pdf`         | Upload and ingest a PDF for RAG   |

---

## 🧠 How Memory Works

- **Short-term** — Every message is saved to SQLite under a `chat_id`. When you reopen a chat, messages are reloaded from the DB.
- **Long-term** — After every conversation turn, an LLM extracts important user facts (name, preferences, goals, etc.) and saves them to ChromaDB. These are retrieved semantically on every new query.
- **RAG** — Uploaded PDFs are chunked with LangChain's `RecursiveCharacterTextSplitter` and stored in a separate ChromaDB collection. Queried when `mode = rag`.

---

## 🛠️ Tech Stack

| Layer                  | Technology                       |
| ---------------------- | -------------------------------- |
| LLM                    | Groq (`llama-3.3-70b-versatile`) |
| Agent Framework        | LangGraph                        |
| Backend                | FastAPI                          |
| Frontend               | Streamlit                        |
| Short-term Memory      | SQLite                           |
| Long-term Memory + RAG | ChromaDB                         |
| Web Search             | DuckDuckGo (`ddgs`)              |
| PDF Parsing            | pypdf + LangChain Text Splitter  |
| LLM Client             | OpenAI-compatible SDK            |

---

## 👤 Author

**Yash Agarwal**
Fresher @ TCS | ML/AI Engineer in progress
[GitHub](https://github.com/YashAgarwalTheWiz)
