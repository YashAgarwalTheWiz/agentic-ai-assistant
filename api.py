import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import uuid
from memory.short_term import get_all_chats, create_chat, get_messages, init_db
from nodes.tools.rag import ingest_pdf
from agent import workflow
from memory.approvals import init_approvals_db
from nodes.tools.registry import missing_required
from langgraph.types import Command

UPLOAD_DIR = "uploaded_pdfs"


class ChatRequest(BaseModel):
    user_input: str
    chat_id: str


app = FastAPI()


class ValidateRequest(BaseModel):
    tool: str
    arguments: dict


@app.post('/validate_args')
def validate_args(req: ValidateRequest):
    return {"missing": missing_required(req.tool, req.arguments)}



@app.on_event("startup")
def startup():
    init_db()
    init_approvals_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get('/chats')
def get_all_chats_api():
    return get_all_chats()


@app.post('/new_chat')
def create_chat_api():
    return create_chat()


@app.post('/chat')
def post_chat(chat: ChatRequest):
    thread_id = f"{chat.chat_id}:{uuid.uuid4()}"

    initial_state = {
        'messages': [],
        'chat_id': chat.chat_id,
        'thread_id': thread_id,
        'user_input': chat.user_input,
        'long_term_memory': '',
        'response': '',
        'steps': 0,
    }
    result = workflow.invoke(initial_state, config=_config(thread_id))
    return _shape(result, thread_id)


@app.post('/upload_pdf')
async def upload_pdf(pdf: UploadFile = File(...)):
    contents = await pdf.read()
    path = os.path.join(UPLOAD_DIR, pdf.filename)
    with open(path, 'wb') as f:
        f.write(contents)
    try:
        chunks = ingest_pdf(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Ingested {pdf.filename} into {chunks} chunks."}


@app.get('/messages/{chat_id}')
def get_messages_api(chat_id: str):
    rows = get_messages(chat_id)
    return [{"role": r[2], "content": r[3]} for r in rows]

def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _interrupt_payload(result):
    """Return the pending approval payload, or None if the run completed."""
    raised = result.get("__interrupt__") if isinstance(result, dict) else None
    if not raised:
        return None
    first = raised[0]
    return getattr(first, "value", first)


def _shape(result, thread_id: str) -> dict:
    pending = _interrupt_payload(result)
    if pending:
        return {
            "status": "pending_approval",
            "thread_id": thread_id,
            "actions": pending.get("actions", []),
            "response": None,
            "tools_used": [],
            "steps": result.get("steps", 0),
        }

    tools_used = [
        m['name'] for m in result.get('messages', []) if m.get('role') == 'tool'
    ]
    return {
        "status": "complete",
        "thread_id": thread_id,
        "response": result.get('response', ''),
        "tools_used": [e["name"] for e in result.get('executed_tools', [])],
        "steps": result.get('steps', 0),
    }



class ResumeRequest(BaseModel):
    thread_id: str
    # tool_call_id -> "approve" | "cancel"
    #             or {"decision": "approve", "arguments": {...}}
    decisions: dict


@app.post('/resume')
def resume_chat(req: ResumeRequest):
    try:
        result = workflow.invoke(
            Command(resume=req.decisions), config=_config(req.thread_id)
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not resume thread {req.thread_id}: {type(e).__name__}: {e}",
        )
    return _shape(result, req.thread_id)