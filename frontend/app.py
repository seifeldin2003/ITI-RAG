"""Streamlit chat UI for the automotive diagnostic assistant."""
import streamlit as st

from api_client import ApiError, ask, health

st.set_page_config(page_title="Automotive Diagnostic Assistant", page_icon="🚗")
st.title("🚗 Automotive Diagnostic Assistant")
st.caption(
    "Ask about a car problem — answers are grounded in real NHTSA recall/complaint "
    "records and mechanic-authored DTC references, with citations. Not medical or "
    "legal advice; always confirm safety-critical repairs with a qualified mechanic."
)

status = health()
if status is None:
    st.error(
        "⚠️ Can't reach the backend. Is it running? "
        "(`uvicorn app.main:app --reload` from the `backend/` folder)"
    )
elif status.get("chunks_indexed"):
    st.caption(f"Backend connected — {status['chunks_indexed']:,} reference chunks indexed.")

if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        st.write(turn["answer"])
        if turn["sources"]:
            st.caption("Sources: " + ", ".join(turn["sources"]))

question = st.chat_input("e.g. my BMW X6 can't put on drive mode")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Looking through recall, complaint, and diagnostic records..."):
            try:
                result = ask(question)
                answer, sources = result["answer"], result["sources"]
            except ApiError as e:
                answer, sources = f"Sorry, something went wrong: {e}", []

        st.write(answer)
        if sources:
            st.caption("Sources: " + ", ".join(sources))

    st.session_state.history.append({"question": question, "answer": answer, "sources": sources})
