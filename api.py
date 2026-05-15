from fastapi import FastAPI, File, UploadFile
from memory.short_term import get_all_chats,create_chat,get_messages
from nodes.tools.rag import ingest_pdf
from agent import workflow
from pydantic import BaseModel
from memory.short_term import get_all_chats, create_chat, init_db

class ChatRequest(BaseModel):
    user_input: str
    chat_id: str
    query_type:str=''

app=FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.get('/chats')
def get_all_chats_api():
    res=get_all_chats()
    return res

@app.post('/chat')
def post_chat(chat:ChatRequest):
    initial_state={
        'user_input':chat.user_input,
        'chat_id':chat.chat_id,
        'long_term_memory': '',
        'query_type': chat.query_type,
        'response': '',
        'tool_result': ''
    }
    res=workflow.invoke(initial_state)
    return res

@app.post('/new_chat')
def create_chat_api():
    return create_chat()

@app.post('/upload_pdf')
async def upload_pdf(pdf: UploadFile = File(...)):
    contents = await pdf.read()
    path = f"uploaded_pdfs/{pdf.filename}"
    with open(path, 'wb') as f:
        f.write(contents)
    ingest_pdf(path)
    return {"message": "PDF uploaded successfully"}

@app.get('/messages/{chat_id}')
def get_messages_api(chat_id:str):
    messages=get_messages(chat_id=chat_id)
    formatted = [{"role": m[2], "content": m[3]} for m in messages]
    return formatted