# HR Policy Assistant

A Retrieval-Augmented Generation (RAG) application for answering employee questions using uploaded HR policy documents.

The system retrieves relevant sections from the uploaded policies and uses an LLM to generate an answer grounded only in that retrieved content. If the policies do not contain enough information to answer a question, the system refuses to answer rather than relying on outside knowledge.

## Features

- Upload HR policy documents in Markdown format
- Section-aware document chunking
- Local semantic embeddings using `all-MiniLM-L6-v2`
- ChromaDB vector store for retrieval
- Semantic relevance filtering
- LLM-based answer generation using Gemini
- Structured JSON responses
- Citations containing document name and policy section
- Citation validation against retrieved documents
- Refusal when the policies do not contain the answer
- FastAPI backend
- Streamlit frontend
- Protection against empty, oversized, and unsafe file uploads

## Architecture

The application follows a standard Retrieval-Augmented Generation pipeline:
```text
                 ┌──────────────────┐
                 │  Policy Document │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Load & Chunk     │
                 │ by Sections      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Local Embeddings │
                 │ MiniLM-L6-v2     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │    ChromaDB      │
                 └────────┬─────────┘
                          │
                          │
User Question ────────────┤
                          ▼
                 ┌──────────────────┐
                 │ Query Embedding  │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Semantic Search  │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Relevance Filter │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Gemini LLM       │
                 │ Answer Generation│
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Citation         │
                 │ Validation       │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Structured JSON  │
                 └──────────────────┘
   ```
## Project Structure
```text
hr_policy_assistant/
│
├── app/
│   ├── __init__.py
│   ├── ingestion.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── generation.py
│   └── main.py
│
├── data/
│   ├── benefits-policy.md
│   ├── it-security-policy.md
│   └── leave-policy.md
│
├── uploads/
├── chroma_db/
│
├── frontend.py
├── tests/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
uploads/ and chroma_db/ are generated at runtime and are excluded from Git.

## Technologies
Python — application language
FastAPI — backend API
Streamlit — simple web interface
ChromaDB — vector database
Sentence Transformers — local text embeddings
Gemini — answer generation
Pydantic — request and response validation

# Models
## Embedding Model

The project uses:

### all-MiniLM-L6-v2

This model runs locally and generates 384-dimensional embeddings.

Using a local embedding model avoids requiring a separate embedding API and keeps the retrieval layer inexpensive.

## Generation Model

The application uses Gemini for answer generation.

The API key is loaded from an environment variable and is not stored in the source code.

# Setup
1. Clone the repository
   git clone <repository-url>
   cd hr_policy_assistant
2. Create a virtual environment

## Windows:

   python -m venv .venv
   .venv\Scripts\activate

## Linux/macOS:

   python -m venv .venv
   source .venv/bin/activate
3. Install dependencies
   pip install -r requirements.txt
4. Configure the Gemini API key

   Create a .env file in the project root:

   GEMINI_API_KEY=your_api_key_here

   The .env file is ignored by Git.

   A template is provided in:

   .env.example
## Running the Application

   The application has two components:

### FastAPI backend
### Streamlit frontend
1. Start the backend

   From the project root:

   uvicorn app.main:app --reload

   The API will be available at:

   http://127.0.0.1:8000

   Interactive API documentation is available at:

   http://127.0.0.1:8000/docs

2. Start the frontend

   Open another terminal, activate the virtual environment, and run:

   streamlit run frontend.py

   Streamlit will display the local URL for the web interface.

## Using the Application
   Upload a policy

   Use the Admin — Upload Policy section in the frontend.

   Select a Markdown (.md) HR policy document and click Upload Policy.

   The backend will:

1. Read the document
2. Split it into section-aware chunks
3. Generate embeddings
4. Store the chunks and metadata in ChromaDB

Each chunk stores metadata including:

### document_name
### section

This metadata is later used to produce citations.

  Ask a question

  Enter a natural-language question in the query box.

  For example:

  How many casual leave days can I carry forward?

  The system retrieves relevant policy sections and generates an answer from those sections.

  The response contains:
  {
  "answer": "...",
  "citations": [
    {
      "document": "leave-policy.md",
      "section": "4.1 Casual leave carry-forward"
    }
  ]
}
### Questions outside the policies

If the uploaded policies do not contain enough information to answer a question, the application returns a refusal instead of guessing.
{
  "answer": "The uploaded HR policies do not contain the answer.",
  "citations": []
}

## API
### POST /upload

   Uploads and indexes a Markdown policy document.

### POST /query

   Accepts a natural-language policy question.
#### Request:
{
  "query": "How many casual leave days can I carry forward?"
}
#### Response:
{
  "answer": "...",
  "citations": [
    {
      "document": "leave-policy.md",
      "section": "4.1 Casual leave carry-forward"
    }
  ]
}

## Retrieval

   The retrieval pipeline uses semantic similarity rather than exact keyword matching.

   For each user query:

   1. Generate an embedding for the query.
   2. Search ChromaDB for the closest policy chunks.
   3. Apply a relevance threshold.
   4. Pass relevant chunks to the generation model.

   The relevance threshold prevents obviously unrelated retrieved chunks from being passed to the LLM.

   The system retrieves multiple chunks rather than only the single closest chunk because the information required to answer a question may occur in a lower-ranked result.
## Chunking Strategy

   Documents are split using Markdown headings.
   Example:
   ### 4. Carry-forward and encashment

   ...

   ### 4.1 Casual leave carry-forward

   ...
   The resulting chunks retain the section heading as metadata.

   This was chosen instead of blindly splitting documents by character count because HR policies are naturally organized into meaningful sections, and preserving those boundaries also makes citations more useful.

## Grounding and Citations

   The generation prompt instructs the model to:

   1. Use only the retrieved policy context
   2. Avoid outside knowledge
   3. Refuse when the context is insufficient
   4. Cite only sections that support the answer

   After generation, citations are validated against the chunks actually retrieved for that query.

   This prevents the model from returning an arbitrary document or section that was not part of the retrieved context.
## Re-uploading Documents

   If a document with the same filename is uploaded again, its existing chunks are removed before the new chunks are indexed.

   Therefore, re-uploading a policy replaces its current indexed content rather than creating duplicate chunks.

## Error Handling

   The backend handles several invalid-input cases:

   1. Empty queries
   2. Missing filenames
   3. Unsupported file extensions
   4. Oversized files
   5. Empty documents
   6. Documents that contain no usable content
   7. Unreadable documents
## Current Limitations

   The current implementation intentionally focuses on the core RAG workflow.

   Current limitations include:

1. Markdown documents only
2. Basic semantic retrieval
3. No hybrid keyword + semantic search
4. No reranking model
5. No document version history
6. No automated evaluation dataset
7. No PDF/table extraction

   These can be addressed as future improvements.
## Future Improvements

   Potential improvements include:

1. Hybrid BM25 + vector retrieval
2. Query normalization for abbreviations such as CL, SL, and PL
3. Reranking retrieved chunks
4. PDF ingestion
5. Automated retrieval and answer evaluation
6. Document versioning
7. User feedback
8. Asynchronous document ingestion

## Security

   API keys must be stored in environment variables.

   Do not commit .env or other secrets to the repository.

   Runtime-generated ChromaDB and uploaded documents are also excluded from Git.