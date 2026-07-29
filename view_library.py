"""
view_library.py

Step 2 of the home library project: a bare-bones viewer for whatever
is currently in library.db. No search or filters yet — just a table
so you can see your library.

Usage:
    streamlit run view_library.py

Must be run from the same folder as library.db (the file ingest_book.py creates).
"""

from pathlib import Path

import sqlite3
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "library.db"

st.set_page_config(page_title="My library", layout="wide")
st.title("My library")

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(
    "SELECT title, author, genre, language, publication_year, isbn FROM books ORDER BY title",
    conn,
)
conn.close()

st.write(f"{len(df)} book(s) in your library")
st.dataframe(df, width="stretch", hide_index=True)