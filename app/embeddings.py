from sentence_transformers import SentenceTransformer
model_name="all-MiniLM-L6-v2"
model=SentenceTransformer(model_name)
def embed_texts(texts: list[str]) -> list[list[str]]:
    embeddings=model.encode(texts)
    return embeddings.tolist()
def embed_text(text: str) -> list[str]:
    embedding=model.encode([text])[0]
    return embedding.tolist()
if __name__ == "__main__":
    text1 = "How many casual leave days can I carry forward?"
    text2 = "What is the maximum number of CL days I can carry over?"
    text3 = "How do I report a phishing incident?"

    embedding1 = embed_text(text1)
    embedding2 = embed_text(text2)
    embedding3 = embed_text(text3)

    print("Embedding length:", len(embedding1))
    print("First 5 values:", embedding1[:5])