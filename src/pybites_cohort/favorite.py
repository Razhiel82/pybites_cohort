import httpx
import streamlit as st
from decouple import config

API_URL = config("API_URL")

st.markdown("### Toggle Favorite")
st.sidebar.markdown("# 🪃 Toggle Favorite")

with st.form(key="toggle_favorite_form"):
    snippet_id = st.number_input("Snippet ID", min_value=1)
    submit = st.form_submit_button("Toggle Favorite")

if submit:
    get_response = httpx.get(f"{API_URL}/snippets/{snippet_id}")
    if get_response.status_code == 200:
        snippet_data = get_response.json()
        is_favorite = snippet_data.get("favorite")

        try:
            if is_favorite:
                toggle_response = httpx.post(f"{API_URL}/snippets/{snippet_id}/fav_off")
                message = "Snippet unmarked as favorite."
            else:
                toggle_response = httpx.post(f"{API_URL}/snippets/{snippet_id}/fav_on")
                message = "Snippet marked as favorite."

            if toggle_response.status_code == 200:
                st.success(message)
            else:
                try:
                    error_detail = toggle_response.json().get(
                        "detail", toggle_response.text
                    )
                except Exception:
                    error_detail = toggle_response.text
                st.error(f"Error toggling favorite: {error_detail}")
        except httpx.RequestError as e:
            st.error(f"Network error while toggling favorite: {e}")
    else:
        try:
            error_detail = get_response.json().get("detail", get_response.text)
        except Exception:
            error_detail = get_response.text
        st.error(f"Error fetching snippet: {get_response.status_code} - {error_detail}")
