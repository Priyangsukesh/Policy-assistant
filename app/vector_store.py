from pathlib import Path

import chromadb

from app.embeddings import embed_text, embed_texts
from app.ingestion import load_document, chunk_document


CHROMA_PATH = "chroma_db"
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="hr_policies"
)
def add_chunks(chunks: list[dict]):
    if not chunks:
        return

    document_name = chunks[0]["metadata"]["document_name"]

    # Remove existing chunks for this document
    collection.delete(
        where={"document_name": document_name}
    )

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts)

    ids = [
        f"{document_name}_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [chunk["metadata"] for chunk in chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

def index_document(file_path: str):
    document_name = Path(file_path).name

    try:
        text = load_document(file_path)
    except Exception as e:
        raise ValueError(
            f"Could not read document: {e}"
        )

    if not text.strip():
        raise ValueError(
            "The uploaded document is empty."
        )

    chunks = chunk_document(text, document_name)

    if not chunks:
        raise ValueError(
            "The uploaded document contains no usable content."
        )

    add_chunks(chunks)

    return len(chunks)

def search(query: str, n_results: int = 3):
    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    cleaned_results = []

    for i in range(len(results["documents"][0])):
        cleaned_results.append({
            "text": results["documents"][0][i],
            "document": results["metadatas"][0][i]["document_name"],
            "section": results["metadatas"][0][i]["section"],
            "distance": results["distances"][0][i]
        })

    return cleaned_results
def get_relevant_chunks(query: str, n_results: int = 3, threshold: float = 1.5):
    results = search(query, n_results)

    relevant_results = [
        result for result in results
        if result["distance"] <= threshold
    ]

    return relevant_results
if __name__ == "__main__":
    query = "What is Incident reporting?"

    results = search(query, n_results=3)

    for i, result in enumerate(results, start=1):
        print("\n" + "=" * 50)
        print(f"RESULT {i}")
        print("=" * 50)
        print("Document:", result["document"])
        print("Section:", result["section"])
        print("Distance:", result["distance"])
        print("Text:", result["text"])