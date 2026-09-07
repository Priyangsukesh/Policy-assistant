import os
from dotenv import load_dotenv
from google import genai
from app.vector_store import get_relevant_chunks
load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)
from pydantic import BaseModel


class Citation(BaseModel):
    document: str
    section: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
def build_context(results: list[dict]) -> str:
    context_parts = []

    for result in results:
        context_parts.append(
            f"Document: {result['document']}\n"
            f"Section: {result['section']}\n"
            f"Content:\n{result['text']}"
        )

    return "\n\n---\n\n".join(context_parts)
def generate_answer(query: str, context: str) -> str:
    prompt = f"""
You are an HR policy assistant.

Answer the user's question using ONLY the policy context provided below.

If the context does not contain enough information to answer the question,
say that the uploaded HR policies do not contain the answer.
Do not use outside knowledge or make assumptions.

Policy context:
{context}

User question:
{query}
"""

    response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": AnswerResponse,
    }
)

    return AnswerResponse.model_validate_json(response.text)
def validate_citations(
    answer: AnswerResponse,
    results: list[dict]
) -> AnswerResponse:

    valid_citations = []

    for citation in answer.citations:
        for result in results:
            if (
                citation.document == result["document"]
                and citation.section == result["section"]
            ):
                valid_citations.append(citation)
                break

    return AnswerResponse(
        answer=answer.answer,
        citations=valid_citations
    )
def answer_query(query: str) -> AnswerResponse:
    results = get_relevant_chunks(
        query,
        n_results=3
    )

    if not results:
        return AnswerResponse(
            answer="The uploaded HR policies do not contain the answer.",
            citations=[]
        )

    context = build_context(results)

    answer = generate_answer(query, context)

    answer = validate_citations(answer, results)

    return answer
if __name__ == "__main__":
    answer=answer_query("Data classification?")
    print("\nANSWER:")
    print(answer.answer)

    print("\nCITATIONS:")
    for citation in answer.citations:
        print("Document:", citation.document)
        print("Section:", citation.section)
    