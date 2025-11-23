import httpx
import streamlit as st
from decouple import config

API_URL = config("API_URL")

st.markdown("### 🏷️ Add Tag")
st.sidebar.markdown("# 🏷️ Add Tag")

with st.form(key="add_tag_form"):
    snippet_id = st.number_input("Snippet ID", min_value=1)
    tag_name = st.text_input("Tag Name")
    submit = st.form_submit_button("Add Tag")

if submit:
    tag_names = [tag_name] if tag_name else []
    payload = {"tags": tag_names}
    response = httpx.post(f"{API_URL}/snippets/{snippet_id}/tags", json=payload)
