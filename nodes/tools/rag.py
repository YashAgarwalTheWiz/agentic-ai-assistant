from pypdf import PdfReader
import chromadb
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from nodes.tools.registry import tool
import os

def init_rag():
    client = chromadb.PersistentClient(path='./chroma_db')
    return client.get_or_create_collection(name='rag')

rag_collection = init_rag()


def ingest_pdf(file_path: str) -> int:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"

    if not text.strip():
        raise ValueError(
            "No extractable text found. This PDF is probably a scan and needs OCR."
        )

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    base = os.path.basename(file_path)
    rag_collection.upsert(
        documents=chunks,
        ids=[f"{base}:{i}" for i in range(len(chunks))],
        metadatas=[{"source": base} for _ in chunks],
    )
    return len(chunks)


@tool(
    name="search_documents",
    description=(
        "Search the user's own uploaded PDF document(s) for a specific answer "
        "contained within them. Use this ONLY when the user is asking about "
        "their own uploaded material specifically -- for example, they say "
        "'my document', 'the paper I uploaded', 'according to the PDF', or ask "
        "a direct follow-up about something already discussed from an uploaded "
        "file. Do NOT use this for a general technical, scientific, or academic "
        "question just because it sounds like something a paper might cover -- "
        "questions like 'explain how photosynthesis works' or 'what is gradient "
        "descent' are general knowledge and should be answered directly, even "
        "if an uploaded document happens to use similar vocabulary or is on a "
        "related topic. If unsure whether the question is about the user's "
        "specific document versus general knowledge, prefer answering directly."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The specific thing to look for in the documents. Use the key "
                    "terms you expect to appear in the text, not the user's full "
                    "sentence. Example: 'joining date and salary' rather than "
                    "'what does my offer letter say about when I start and what "
                    "I'll be paid'."
                ),
            }
        },
        "required": ["query"],
    },
)
def search_documents(query: str) -> str:
    results = rag_collection.query(query_texts=[query], n_results=5)
    docs = results['documents'][0] if results['documents'] else []
    metas = results['metadatas'][0] if results['metadatas'] else []
    if not docs:
        return "No documents have been uploaded yet, or nothing matched that query."
    return "\n---\n".join(
        f"[from {m.get('source', 'unknown')}] {d}" for d, m in zip(docs, metas)
    )


def list_documents() -> list[str]:
    """Distinct source filenames currently in the collection."""
    try:
        metas = rag_collection.get(include=['metadatas'])['metadatas']
        return sorted({m.get('source', 'unknown') for m in metas})
    except Exception:
        return []