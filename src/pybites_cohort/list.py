import httpx
import pandas as pd
import streamlit as st
from decouple import config

API_URL = config("API_URL")

st.markdown("# 📄 List Snippets")
st.sidebar.markdown("# 📄 List Snippets")

response = httpx.get(f"{API_URL}/snippets/")
data = response.json()

df = pd.DataFrame(data)

st.dataframe(df, hide_index=True)
