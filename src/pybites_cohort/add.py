import httpx
import streamlit as st
from decouple import config

from pybites_cohort.models import Language

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
    tag_names = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
    payload = {
        "title": title,
        "code": code,
        "description": description,
        "language": Language[language].value,  # z.B. "py"
        "favorite": favorite,
        "tags": tag_names,  # Liste von Strings
    }
    response = httpx.post(f"{API_URL}/snippets/", json=payload)
