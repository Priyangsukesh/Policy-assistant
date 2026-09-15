from pathlib import Path

import streamlit as st

from app.generation import answer_query
from app.vector_store import index_document


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024


st.title("HR Policy Assistant")

st.write(
    "Ask questions about the uploaded HR policies."
)


# ==========================================
# Admin - Upload Policy
# ==========================================

st.subheader("Admin — Upload Policy")


uploaded_file = st.file_uploader(
    "Upload a Markdown or PDF policy document",
    type=["md", "pdf"]
)


if st.button("Upload Policy"):

    if uploaded_file is None:

        st.warning(
            "Please select a file."
        )

    else:

        safe_filename = Path(
            uploaded_file.name
        ).name

        contents = uploaded_file.getvalue()

        if len(contents) > MAX_FILE_SIZE:

            st.error(
                "File is too large. Maximum size is 5 MB."
            )

        else:

            file_path = (
                UPLOAD_DIR / safe_filename
            )

            file_path.write_bytes(contents)

            try:

                chunk_count = index_document(
                    str(file_path)
                )

                st.success(
                    "Policy uploaded and indexed successfully."
                )

                st.write(
                    f"**Document:** {safe_filename}"
                )

                st.write(
                    f"**Chunks indexed:** {chunk_count}"
                )

            except ValueError as e:

                file_path.unlink(
                    missing_ok=True
                )

                st.error(str(e))


st.divider()


# ==========================================
# Ask Question
# ==========================================

st.subheader("Ask a Question")


query = st.text_input(
    "Enter your HR policy question"
)


if st.button("Ask"):

    if not query.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        try:

            result = answer_query(
                query.strip()
            )

            st.subheader("Answer")

            for item in result.answers:

                st.markdown(
                    f"### {item.question}"
                )

                st.write(
                    item.answer
                )

                st.markdown(
                    "**Citations:**"
                )

                if item.citations:

                    for citation in item.citations:

                        st.write(
                            f"- **{citation.document}** — "
                            f"{citation.section}"
                        )

                else:

                    st.write(
                        "No citations."
                    )

                st.divider()

        except Exception as e:

            st.error(
                f"An error occurred: {e}"
            )