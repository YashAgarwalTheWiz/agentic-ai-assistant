from pypdf import PdfReader
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid

def init_rag():
    client=chromadb.PersistentClient(path='./chroma_db')
    collection=client.get_or_create_collection(name='rag')
    return collection


def ingest_pdf(file_path:str):
    reader=PdfReader(file_path)
    text=""
    for page in reader.pages:
        text+=page.extract_text()
    splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
    chunks=splitter.split_text(text)
    for chunk in chunks:
        rag_collection.add(
            documents=[chunk],
            ids=[str(uuid.uuid4())],
            metadatas=[{"source": file_path}]
        )


def query_rag(query:str)->str:
    results=rag_collection.query(
        query_texts=[query],
        n_results=5
    )
    return '\n'.join(results['documents'][0])


rag_collection=init_rag()