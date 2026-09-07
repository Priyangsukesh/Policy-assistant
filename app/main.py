from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, field_validator

from app.generation import answer_query
from app.vector_store import index_document


app = FastAPI(title="HR Policy Assistant")


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class QueryRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):
        if not value.strip():
            raise ValueError("Query cannot be empty.")
        return value.strip()


@app.post("/query")
def query_policy(request: QueryRequest):
    return answer_query(request.query)


@app.post("/upload")
async def upload_policy(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    if not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="Only Markdown (.md) files are supported."
        )
    safe_filename = Path(file.filename).name
    file_path = UPLOAD_DIR / safe_filename

    contents = await file.read()
    MAX_FILE_SIZE = 5 * 1024 * 1024 
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the maximum limit of 5MB."
        )
    file_path.write_bytes(contents)

    try:
        chunk_count = index_document(str(file_path))
    except ValueError as e:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
        status_code=400,
        detail=str(e)
    )

    return {
        "message": "Policy uploaded and indexed successfully.",
        "document": safe_filename,
        "chunks_indexed": chunk_count
    }