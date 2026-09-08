# HR Policy Assistant — Design Document

## 1. Overview

The HR Policy Assistant is a Retrieval-Augmented Generation (RAG) system that answers employee questions using uploaded HR policy documents.

The system follows a retrieval-first approach. Policy documents are loaded, divided into meaningful sections, embedded using a local embedding model, and stored in ChromaDB. When an employee asks a question, the question is embedded and used to retrieve semantically relevant policy sections.

Only sufficiently relevant retrieved sections are passed to the generation model. The model is instructed to answer using only the provided policy context and to refuse when the retrieved policies do not contain enough information.

The final response is returned as structured JSON containing the answer and citations identifying the source document and policy section.

## 2. Architecture

The system consists of the following components:

- **Document ingestion** — loads uploaded Markdown policy files and converts them into section-aware chunks.
- **Embedding layer** — generates vector representations using `all-MiniLM-L6-v2`.
- **Vector store** — stores embeddings, document text, and metadata in ChromaDB.
- **Retrieval layer** — embeds the user's query and retrieves the most semantically similar chunks.
- **Relevance filtering** — removes retrieved chunks whose semantic distance is above the configured threshold.
- **Generation layer** — passes the retrieved policy context to Gemini to generate a grounded answer.
- **Citation validation** — verifies that returned citations correspond to documents and sections that were actually retrieved.
- **FastAPI backend** — exposes document upload and question-answering APIs.
- **Streamlit frontend** — provides a simple interface for administrators to upload policies and employees to ask questions.

### Data Flow

#### Document ingestion

```text
                    Uploaded Policy
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       Markdown (.md)          PDF (.pdf)
              │                     │
              │                     ▼
              │             PDF text & table
              │                extraction
              │                     │
              │                     ▼
              │              Markdown
              │              representation
              │                     │
              └──────────┬──────────┘
                         │
                         ▼
                Section-aware chunking
                         │
                         ▼
                  Generate embeddings
                         │
                         ▼
                     ChromaDB
                         │
                         ▼
                  Ready for retrieval
```

## 3. Chunking Strategy

The system uses section-aware chunking based on Markdown headings.

Instead of splitting the policy documents into arbitrary fixed-size pieces, the ingestion layer identifies Markdown headings (`#`, `##`, and `###`) and creates chunks around those sections.

Each chunk contains:

- The policy content belonging to that section
- The document name
- The section heading

For example:

Document: leave-policy.md
Section: 4.1 Casual leave carry-forward

Content:
Employees may carry forward a maximum of 8 days...

### PDF Processing

PDF documents are first converted into Markdown using PyMuPDF4LLM.

The extraction process preserves normal document text and detected tables in Markdown form. The resulting Markdown representation is then passed through the same section-aware chunking pipeline used for native Markdown documents.

This allows PDF and Markdown documents to share the same downstream retrieval architecture:

```text
PDF
 ↓
PDF text/table extraction
 ↓
Markdown representation
 ↓
Section-aware chunking
 ↓
Embeddings
 ↓
ChromaDB
```

## 4. Retrieval Strategy

The system uses semantic vector search for retrieval.

Both policy chunks and user queries are converted into embeddings using `all-MiniLM-L6-v2`.

When a user submits a question:

1. The question is converted into an embedding.
2. ChromaDB compares the query embedding with stored chunk embeddings.
3. The top `k` closest chunks are retrieved.
4. A relevance threshold is applied to the retrieved chunks.
5. Only chunks that pass the threshold are provided to the generation model.

The current retrieval configuration retrieves up to three candidate chunks.

### Why semantic retrieval?

Keyword matching can fail when the user and policy use different wording.

For example, a user might ask:

> "How much casual leave can I save for next year?"

while the policy uses:

> "carry forward"

Semantic embeddings allow the system to recognize that these expressions are related even when the exact words do not match.

### Why retrieve multiple chunks?

The closest chunk is not always sufficient to answer a question.

A policy rule may be described across multiple sections, and the most useful supporting section may not be the first-ranked result.

Therefore, the system retrieves multiple candidates before generating the answer.

### Relevance threshold

Semantic similarity alone does not guarantee that a retrieved chunk actually contains the answer.

For this reason, the system applies a distance threshold after retrieval. Chunks whose distance is above the configured threshold are discarded.

The threshold is an empirical configuration selected for the current embedding model and policy dataset rather than a universal value.

If no chunks pass the threshold, the system refuses to answer.

## 5. Grounding and Citation Strategy

Grounding is enforced at multiple stages of the pipeline.

First, only retrieved policy chunks that pass the relevance threshold are provided to the generation model.

The generation prompt explicitly instructs the model to:

- Use only the provided policy context.
- Not use outside knowledge.
- Not make assumptions.
- Refuse when the provided context does not contain enough information.
- Cite only sections that actually support the answer.

The generation model returns a structured response containing an answer and a list of citations.

After generation, the backend validates every citation against the chunks retrieved for the current query.

A citation is retained only when its document name and section match one of the retrieved chunks.

This provides an additional safeguard against the model producing citations that were not part of the retrieved context.

If retrieval produces no sufficiently relevant chunks, the generation step is skipped and the system directly returns a refusal with an empty citation list.

## 6. Response Schema

The API uses Pydantic models to enforce a consistent response structure.

The response contains an `answer` and a list of `citations`.

Each citation contains:

- `document` — name of the source policy document
- `section` — section containing the supporting information

Example:

```json
{
  "answer": "Employees may carry forward a maximum of 8 days of casual leave.",
  "citations": [
    {
      "document": "leave-policy.md",
      "section": "4.1 Casual leave carry-forward"
    }
  ]
}
For questions that cannot be answered from the uploaded documents, the response will be like:{
  "answer": "The uploaded HR policies do not contain the answer.",
  "citations": []
}
```

## 7. API Design

The FastAPI backend exposes two primary endpoints.

### `POST /upload`

Accepts a Markdown policy document.

The ingestion flow:

```text
Upload file
    ↓
Validate filename and extension
    ↓
Validate file size
    ↓
Save file
    ↓
Load document
    ↓
Validate document content
    ↓
Chunk document
    ↓
Generate embeddings
    ↓
Store in ChromaDB
```
---

## 8. Design Trade-offs

### Section-aware chunking vs fixed-size chunking

Section-aware chunking was chosen because the supplied HR policies are structured using Markdown headings.

This keeps related policy rules together and produces meaningful citation sections.

The trade-off is that very large sections could exceed the ideal context size. For larger or more complex documents, an additional token- or character-based splitting strategy could be introduced.

### Local embeddings vs hosted embeddings

`all-MiniLM-L6-v2` was selected for embeddings because it can run locally and does not require a separate embedding API.

This reduces external dependencies and cost.

The trade-off is that larger hosted embedding models may provide better retrieval quality for difficult queries.

### ChromaDB vs a larger vector database

ChromaDB was selected because the assignment is small-scale and requires a simple local setup.

It provides the vector search functionality required without requiring an external database service.

For a production system with many documents and users, a more scalable vector database could be considered.

### Semantic retrieval vs hybrid retrieval

The current system uses semantic vector search.

This works well for natural-language questions where the wording differs from the policy.

However, exact terms, abbreviations, policy codes, or short queries can sometimes benefit from keyword matching.

A hybrid BM25 + vector retrieval approach would be a potential improvement.

### Simple relevance threshold vs additional verification

A distance threshold provides a lightweight way to reject obviously unrelated results.

However, distance alone cannot prove that a chunk contains the answer.

The current design therefore combines:

1. Semantic retrieval
2. Relevance filtering
3. LLM grounding instructions
4. Citation validation

A future version could add a dedicated reranker or NLI/claim-verification stage for stronger answer verification.

## 9. Current Limitations

The current implementation intentionally focuses on a small, reliable base RAG system.

Current limitations include:

- Retrieval currently uses semantic vector search rather than hybrid retrieval.
- No dedicated reranking model is currently used.
- The relevance threshold is empirically configured for the current embedding model and dataset.
- Document replacement is based on filename and does not maintain historical versions.
- There is no automated evaluation dataset yet.
- Complex layouts and scanned PDFs may require OCR or specialized extraction techniques.
- The current system is designed for a small collection of HR policy documents rather than large-scale production workloads.

## 10. Two-Week Hardening Plan

If the base system were extended for a more production-oriented environment, the following improvements would be prioritized.

### 1. Improve retrieval

Introduce hybrid retrieval combining semantic vector search with keyword-based retrieval such as BM25.

This would improve performance for:

- Exact policy terminology
- Abbreviations such as CL, SL, and PL
- Specific numbers or policy terms

A reranking stage could then be applied to the retrieved candidates to select the most relevant chunks before generation.

### 2. Add automated evaluation

Create a small evaluation dataset containing representative HR questions and expected supporting policy sections.

Evaluation could measure:

- Retrieval accuracy
- Citation correctness
- Answer correctness
- Refusal accuracy

This would make retrieval and grounding improvements measurable instead of relying only on manual testing.

### 3. Improve PDF extraction

The current system supports PDF text and detected table extraction. Further hardening could improve handling of scanned documents, complex multi-page tables, unusual layouts, and OCR-based extraction.

### 4. Add document versioning

Instead of replacing a document whenever the same filename is uploaded, maintain document versions.

Each indexed chunk could include metadata such as:

- Document version
- Upload timestamp
- Active/inactive status

This would make policy updates auditable.

### 5. Improve ingestion scalability

For larger documents or larger numbers of uploads, document ingestion could be moved to an asynchronous background process.

This would prevent large embedding operations from blocking the upload request.

### 6. Add user feedback

Allow employees to indicate whether an answer was useful.

Feedback could be stored and later used to identify retrieval failures and improve the evaluation dataset.

## 11. Summary

The system uses a simple RAG architecture designed around the primary requirement of answering questions only from uploaded HR policies.

The main design priorities are:

1. Preserve meaningful policy sections during ingestion.
2. Retrieve multiple semantically relevant chunks.
3. Filter obviously irrelevant results before generation.
4. Restrict the LLM to retrieved policy context.
5. Refuse when the available policy context is insufficient.
6. Return structured responses with citations.
7. Validate citations against the retrieved source chunks.

The architecture intentionally avoids unnecessary complexity in the base implementation while leaving clear extension points for hybrid retrieval, reranking, evaluation, document versioning, and additional document formats.