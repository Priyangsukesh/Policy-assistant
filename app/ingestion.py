from pathlib import Path
import re
import pymupdf4llm
def load_document(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() == ".md":
        return path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".pdf":
        return pymupdf4llm.to_markdown(str(path))

    raise ValueError(
        "Unsupported file type. Only Markdown and PDF files are supported."
    )
def chunk_document(content: str, document_name: str) -> list[dict]:
    chunks = []
    current_section="General"
    current_lines=[]
    for line in content.splitlines():
        heading_match=re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading_match:
            if current_lines:
                chunks.append({
                    "text": "\n".join(current_lines).strip(),
                    "metadata": {
                        "document_name": document_name,
                        "section": current_section,
                    }
                })
                current_lines=[]
            current_section=heading_match.group(2).strip()
        else:
            current_lines.append(line)
    if current_lines:
        chunks.append({
            "text": "\n".join(current_lines).strip(),
            "metadata": {
                "document_name": document_name,
                "section": current_section
            }
        })
    return chunks

if __name__ == "__main__":
    file_path = "data/benefits-policy.md"
    content=load_document(file_path)
    chunks=chunk_document(content, "benefits-policy")
    print(len(chunks))
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:\n{chunk}\n")