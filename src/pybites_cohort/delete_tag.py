import httpx
import streamlit as st
from decouple import config

API_URL = config("API_URL")

st.markdown("### 🗑️ Delete Tag")
st.sidebar.markdown("# 🗑️ Delete Tag")


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_all_snippets():
    try:
        response = httpx.get(f"{API_URL}/snippets/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"Error fetching snippets: {response.status_code} - {response.json().get('detail', response.text)}"
            )
    except httpx.RequestError as e:
        st.error(f"Network error while fetching snippets: {e}")
    return []


all_snippets = get_all_snippets()
snippet_options = {f"{s['id']}: {s['title']}" for s in all_snippets}

with st.form(key="delete_tag_form"):
    # Create a mapping from display string to snippet ID
    snippet_display_to_id = {f"{s['id']}: {s['title']}": s["id"] for s in all_snippets}

    # Get sorted display options for the selectbox
    sorted_display_options = sorted(snippet_display_to_id.keys())

    selected_snippet_display = st.selectbox(
        "Select Snippet", options=[""] + sorted_display_options
    )
    snippet_id = snippet_display_to_id.get(
        selected_snippet_display
    )  # Get the actual ID

    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_snippet_tags(s_id):
        try:
            response = httpx.get(f"{API_URL}/snippets/{s_id}")
            if response.status_code == 200:
                snippet_data = response.json()
                return [tag["name"] for tag in snippet_data.get("tags", [])]
            elif response.status_code == 404:
                st.warning(f"Snippet with ID {s_id} not found.")
            else:
                st.error(
                    f"Error fetching snippet: {response.status_code} - {response.json().get('detail', response.text)}"
                )
        except httpx.RequestError as e:
            st.error(f"Network error while fetching snippet: {e}")
        return []

    existing_tags = get_snippet_tags(snippet_id) if snippet_id else []

    # Fetch all existing tags from the API
    all_tags = []
    try:
        response = httpx.get(f"{API_URL}/tags/")
        if response.status_code == 200:
            all_tags = [tag["name"] for tag in response.json()]
    except httpx.RequestError as e:
        st.error(f"Network error while fetching all tags: {e}")
    tag_name = st.text_input("Tag to delete")
    submit = st.form_submit_button("Delete Tag")

if submit:
    if not snippet_id:
        st.warning("Please select a snippet.")
    elif not tag_name:
        st.warning("Please select a tag to delete.")
    elif tag_name not in existing_tags:
        st.warning(f"Tag '{tag_name}' is not associated with the selected snippet.")
    else:
        payload = {"tags": [tag_name], "remove": True}
        response = httpx.post(f"{API_URL}/snippets/{snippet_id}/tags", json=payload)

        if response.status_code == 200:
            st.success(f"Tag '{tag_name}' deleted from snippet {snippet_id}.")
        else:
            st.error(
                f"Error deleting tag: {response.status_code} - {response.json().get('detail', response.text)}"
            )
