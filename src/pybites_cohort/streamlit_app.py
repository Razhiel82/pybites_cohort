# from pybites_cohort.api import list_snippets
import streamlit as st
from decouple import config

API_URL = config("API_URL")
st.set_page_config(page_title="Snipster", page_icon=":tada:", layout="wide")

st.title("Snipster")
st.sidebar.header("Options")

main_page = st.Page("main_page.py", title="Main Page", icon="🏠")
list_page = st.Page("list.py", title="List Snippets", icon="📄")
add_page = st.Page("add.py", title="Add Snippets", icon="➕")
delete_page = st.Page("delete.py", title="Delete Snippets", icon="❌")
add_tag_page = st.Page("add_tag.py", title="Add Tags", icon="🏷️")
delete_tage_page = st.Page("delete_tag.py", title="Delete Tags", icon="🗑️")
favorite_page = st.Page("favorite.py", title="Favorite Snippets", icon="⭐")


pg = st.navigation(
    [
        main_page,
        list_page,
        add_page,
        delete_page,
        add_tag_page,
        delete_tage_page,
        favorite_page,
    ]
)

pg.run()
