import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

from app.vector_store import get_relevant_chunks


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# -----------------------------
# Response schemas
# -----------------------------

class Citation(BaseModel):
    document: str
    section: str


class SubAnswer(BaseModel):
    question: str
    answer: str
    citations: list[Citation]


class AnswerResponse(BaseModel):
    answers: list[SubAnswer]


class QuestionDecomposition(BaseModel):
    sub_questions: list[str]


# -----------------------------
# Question decomposition
# -----------------------------

def decompose_question(query: str) -> list[str]:

    prompt = f"""
You are an HR policy question analyzer.

Determine whether the user's question contains multiple
independently answerable questions.

If it contains multiple questions, split it into separate
sub-questions.

If it is already a single question, return it unchanged.

Do not answer the questions.

Return only the list of sub-questions.

User question:
{query}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": QuestionDecomposition,
        }
    )

    result = QuestionDecomposition.model_validate_json(
        response.text
    )

    return result.sub_questions


# -----------------------------
# Context building
# -----------------------------

def build_context(results: list[dict]) -> str:

    context_parts = []

    for result in results:
        context_parts.append(
            f"Document: {result['document']}\n"
            f"Section: {result['section']}\n"
            f"Content:\n{result['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


def build_multipart_context(
    retrieved_contexts: list[dict]
) -> str:

    context_parts = []

    for item in retrieved_contexts:

        question = item["question"]
        results = item["results"]

        context_parts.append(
            f"Question:\n{question}\n\n"
            f"Relevant policy context:\n"
            f"{build_context(results)}"
        )

    return "\n\n==========\n\n".join(context_parts)


# -----------------------------
# Answer generation
# -----------------------------

def generate_answer(
    query: str,
    context: str
) -> AnswerResponse:

    prompt = f"""
You are an HR policy assistant.

Answer the user's question using ONLY the policy context
provided below.

The user's question may contain multiple independent
sub-questions.

Answer each sub-question separately.

For every sub-question:

1. Give an answer only when the provided policy context
   contains enough information.
2. If the policy context does not contain enough information,
   say that the uploaded HR policies do not contain the answer.
3. Do not use outside knowledge.
4. Do not make assumptions.
5. Provide citations only for policy sections that actually
   support that particular answer.

Return one SubAnswer for each independent question.

Policy context:
{context}

User question:
{query}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": AnswerResponse,
        }
    )

    return AnswerResponse.model_validate_json(
        response.text
    )


# -----------------------------
# Citation validation
# -----------------------------

def validate_citations(
    answer: AnswerResponse,
    retrieved_contexts: list[dict]
) -> AnswerResponse:

    validated_answers = []

    for sub_answer in answer.answers:

        valid_citations = []

        # Find the retrieved chunks belonging to this question
        matching_context = None

        for item in retrieved_contexts:
            if item["question"] == sub_answer.question:
                matching_context = item["results"]
                break

        if matching_context:

            for citation in sub_answer.citations:

                for result in matching_context:

                    if (
                        citation.document
                        == result["document"]
                        and
                        citation.section
                        == result["section"]
                    ):
                        valid_citations.append(citation)
                        break

        validated_answers.append(
            SubAnswer(
                question=sub_answer.question,
                answer=sub_answer.answer,
                citations=valid_citations
            )
        )

    return AnswerResponse(
        answers=validated_answers
    )


# -----------------------------
# Main query pipeline
# -----------------------------

def answer_query(query: str) -> AnswerResponse:

    # Step 1:
    # Break the user's question into independent questions.
    sub_questions = decompose_question(query)

    retrieved_contexts = []

    # Step 2:
    # Retrieve independently for every sub-question.
    for sub_question in sub_questions:

        results = get_relevant_chunks(
            sub_question,
            n_results=3
        )

        retrieved_contexts.append(
            {
                "question": sub_question,
                "results": results
            }
        )

    # Step 3:
    # Build context containing the retrieved chunks
    # for each individual question.
    context = build_multipart_context(
        retrieved_contexts
    )

    # Step 4:
    # Generate all answers in one Gemini call.
    answer = generate_answer(
        query,
        context
    )

    # Step 5:
    # Make sure Gemini can only cite chunks that were
    # actually retrieved for that sub-question.
    answer = validate_citations(
        answer,
        retrieved_contexts
    )

    return answer
if __name__ == "__main__":
    test_query = (
        "How many Casual Leave days can an employee forward and what is the work from home policy?"
    )
    answer = answer_query(test_query)

    for item in answer.answers:
        print(f"Question: {item.question}")
        print(f"Answer: {item.answer}")
        print("Citations:")
        for citation in item.citations:
            print(
                f"- Document: {citation.document}, "
                f"Section: {citation.section}"
            )
        print("\n")