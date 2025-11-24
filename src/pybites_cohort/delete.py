import httpx
import streamlit as st
from decouple import config

API_URL = config("API_URL")

st.markdown("### ❌ Delete Snippet")
st.sidebar.markdown("# ❌ Delete Snippet")


def delete_snippet():
    """Callback function to delete the snippet."""
    snippet_id = st.session_state.get("snippet_id_to_delete")
    if snippet_id:
        try:
            response = httpx.delete(f"{API_URL}/snippets/{snippet_id}")
            # Check for successful deletion (204) or if already deleted (404)
            if response.status_code == 204:
                st.success("Snippet deleted successfully!")
            elif response.status_code == 404:
                st.warning("Snippet was not found. It might have been already deleted.")
            else:
                st.error(f"Error deleting snippet: {response.text}")
        except httpx.ConnectError:
            st.error(
                "Connection to the API failed. Please ensure the API server is running."
            )
        finally:
            # Clear the ID from session state to prevent re-submission
            if "snippet_id_to_delete" in st.session_state:
                del st.session_state["snippet_id_to_delete"]


with st.form(key="delete_snippet_form"):
    st.text_input("ID of snippet to delete", key="snippet_id_to_delete")
    st.form_submit_button("Delete Snippet", on_click=delete_snippet)
