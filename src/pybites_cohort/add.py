import httpx
import streamlit as st
from decouple import config

from pybites_cohort.models import Language, Snippet, Tag

API_URL = config("API_URL")

st.markdown("### ➕ Add Snippet")
st.sidebar.markdown("# ➕ Add Snippet")

with st.form(key="add_snippet_form"):
    title = st.text_input("Title")
    code = st.text_area("Code")
    description = st.text_area("Description")
    language = st.selectbox("Language", [lang.name for lang in Language])
    tags_str = st.text_input("Tags (comma-separated)")
    favorite = st.radio("Favorite", options=[True, False], index=1)

    submit = st.form_submit_button("Add Snippet")

if submit:
    tags = [Tag(name=tag.strip()) for tag in tags_str.split(",") if tag.strip()]
    snippet = Snippet(
        title=title,
        code=code,
        description=description,
        language=Language[language],
        tags=tags,
        favorite=favorite,
    )
    # Create a JSON-serializable representation
    payload = snippet.model_dump()
    # Send POST request to API
    response = httpx.post(f"{API_URL}/snippets/", json=payload)

    if response.status_code == 201:
        st.success("Snippet added successfully!")
    else:
        st.error(f"Error adding snippet: {response.text}")
