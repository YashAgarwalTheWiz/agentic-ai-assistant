import chromadb
import uuid

def init_long_term_memory():
    client=chromadb.PersistentClient(path='./chroma_db')
    collection=client.get_or_create_collection(name='long_term_memory')
    return collection

def save_long_term_memory(collection,text,user_id):
    collection.add(
        documents=[text],
        ids=[str(uuid.uuid4())],
        metadatas=[{"source": "user_profile", "user_id": user_id}]
    )

def get_long_term_memory(collection,query,user_id):
    results=collection.query(
        query_texts=[query],
        n_results=5,
        where={'user_id':user_id}
    )
    return results['documents'][0]

long_term_collection = init_long_term_memory()