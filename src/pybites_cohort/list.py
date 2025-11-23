import httpx
import pandas as pd
import streamlit as st
from decouple import config

API_URL = config("API_URL")


st.markdown("# 📄 List Snippets")
st.sidebar.markdown("# 📄 List Snippets")


try:
    response = httpx.get(f"{API_URL}/snippets/")
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    data = response.json()

    # Process data to make tags readable
    for snippet in data:
        # Extract tag names and join them into a comma-separated string
        tag_names = [
            tag.get("name") for tag in snippet.get("tags", []) if "name" in tag
        ]
        snippet["tags"] = ", ".join(sorted(tag_names))

    df = pd.DataFrame(data)

    # Optionally, select and reorder columns for a cleaner display
    if not df.empty:
        display_columns = [
            "id",
            "title",
            "language",
            "tags",
            "favorite",
            "description",
            "code",
        ]
        # Filter out columns that might not exist in the DataFrame
        existing_columns = [col for col in display_columns if col in df.columns]
        st.dataframe(df[existing_columns], hide_index=True)


except httpx.RequestError as e:
    st.error(f"Connection to the API failed: {e}")
