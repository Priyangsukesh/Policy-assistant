import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"


st.title("HR Policy Assistant")

st.subheader("Admin — Upload Policy")
st.write("Upload HR policy documents in Markdown (.md) or PDF (.pdf) format")
uploaded_file = st.file_uploader(
    "Upload a policy document",
    type=["md", "pdf"]
)
if st.button("Upload Policy"):
    if uploaded_file is None:
        st.warning("Please select a file.")
    else:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "text/markdown" if uploaded_file.type == "text/markdown" else "application/pdf"
            )
        }

        response = requests.post(
            f"{API_URL}/upload",
            files=files
        )

        if response.status_code == 200:
            result = response.json()

            st.success(result["message"])

            st.write(
                f"**Document:** {result['document']}"
            )

            st.write(
                f"**Chunks indexed:** "
                f"{result['chunks_indexed']}"
            )
        else:
            st.error(
                f"Upload failed: {response.text}"
            )

st.divider()
    
st.write(
    "Ask questions about the uploaded HR policies."
)


query = st.text_input(
    "Ask a question"
)


if st.button("Ask"):
    if not query.strip():
        st.warning("Please enter a question.")
    else:
        response = requests.post(
            f"{API_URL}/query",
            json={"query": query}
        )

        if response.status_code == 200:
            result = response.json()

            st.subheader("Answer")
            st.write(result["answer"])

            st.subheader("Citations")

            if result["citations"]:
                for citation in result["citations"]:
                    st.write(
                        f"**{citation['document']}** — "
                        f"{citation['section']}"
                    )
            else:
                st.write("No citations.")
        else:
            st.error(
                f"Request failed: {response.status_code}"
            )