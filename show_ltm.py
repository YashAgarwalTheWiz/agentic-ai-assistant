"""Print everything currently stored in long-term memory."""

import chromadb

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("long_term_memory")

result = collection.get()

if not result["documents"]:
    print("Long-term memory is empty.")
else:
    for doc, meta in zip(result["documents"], result["metadatas"]):
        print(f"- {doc}    {meta}")