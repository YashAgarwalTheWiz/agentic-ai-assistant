import chromadb


def init_long_term_memory():
    client = chromadb.PersistentClient(path='./chroma_db')
    collection = client.get_or_create_collection(name='long_term_memory')
    return collection


def save_long_term_memory(collection, text, user_id):
    # Fixed id per user (not a random uuid) so this UPDATES the existing
    # entry instead of piling up a new duplicate every single turn.
    collection.upsert(
        documents=[text],
        ids=[f"profile:{user_id}"],
        metadatas=[{"source": "user_profile", "user_id": user_id}]
    )


def get_long_term_memory(collection, query, user_id):
    results = collection.query(
        query_texts=[query],
        n_results=5,
        where={'user_id': user_id}
    )
    return results['documents'][0]


long_term_collection = init_long_term_memory()