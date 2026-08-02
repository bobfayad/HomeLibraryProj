"""
view_library.py

Step 3 of the home library project: browse your library with a text
search box plus language/genre filters, as either a cover grid or a
plain table.

Usage:
    streamlit run view_library.py

Must be run from the same folder as library.db (the file ingest_book.py creates).
"""

from pathlib import Path

import html
import sqlite3
import pandas as pd
import streamlit as st

from Ingest_book import create_db, fetch_book_data, insert_book

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "library.db"
GRID_COLUMNS = 5

GRID_STYLE = """
<style>
.book-card { display: flex; flex-direction: column; margin-bottom: 0.5rem; }
.book-cover {
    width: 100%; aspect-ratio: 2 / 3; object-fit: cover !important;
    border-radius: 6px; display: block;
    /* If the URL 404s/times out, the broken image still honors background
       and hides its alt text, so it degrades to a plain box, not an icon. */
    background: linear-gradient(135deg, #d8dee9, #b8c2d1);
    color: transparent;
}
.book-cover-placeholder {
    width: 100%; aspect-ratio: 2 / 3; border-radius: 6px;
    background: linear-gradient(135deg, #d8dee9, #b8c2d1);
    display: flex; align-items: center; justify-content: center;
    padding: 0.75rem; box-sizing: border-box; text-align: center;
}
.book-cover-placeholder span {
    color: #3a3f4b; font-size: 0.85rem; font-weight: 600;
    overflow: hidden; display: -webkit-box;
    -webkit-line-clamp: 5; -webkit-box-orient: vertical;
}
.book-title {
    margin-top: 0.4rem; font-weight: 600; font-size: 0.9rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.book-author {
    font-size: 0.8rem; opacity: 0.65;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>
"""

def render_card(book) -> None:
    """Render one grid cell: cover (or placeholder) + title + author + a details expander."""
    title = html.escape(str(book.title or "Untitled"))
    author = html.escape(str(book.author or "Unknown author"))
    cover_url = (book.cover_url or "").strip()

    if cover_url:
        cover_html = f'<img class="book-cover" src="{html.escape(cover_url)}" alt="{title}">'
    else:
        cover_html = f'<div class="book-cover-placeholder"><span>{title}</span></div>'

    st.markdown(
        f"""
        <div class="book-card">
            {cover_html}
            <div class="book-title" title="{title}">{title}</div>
            <div class="book-author" title="{author}">{author}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Details"):
        st.write(f"**Genre:** {book.genre or 'Unclassified'}")
        st.write(f"**Published:** {book.publication_year or 'Unknown'}")
        st.write(f"**ISBN:** {book.isbn}")


def render_grid(books_df: pd.DataFrame) -> None:
    st.markdown(GRID_STYLE, unsafe_allow_html=True)
    books = list(books_df.itertuples())
    for row_start in range(0, len(books), GRID_COLUMNS):
        row_books = books[row_start : row_start + GRID_COLUMNS]
        cols = st.columns(GRID_COLUMNS)
        for col, book in zip(cols, row_books):
            with col:
                render_card(book)


st.set_page_config(page_title="My library", layout="wide")
st.title("My library")

with st.expander("Add a book"):
    with st.form("add_book_form", clear_on_submit=True):
        isbn_input = st.text_input("ISBN")
        submitted = st.form_submit_button("Add")

    if submitted:
        isbn_input = isbn_input.strip()
        if not isbn_input:
            st.warning("Enter an ISBN.")
        else:
            create_db()
            with st.spinner(f"Fetching {isbn_input}..."):
                book = fetch_book_data(isbn_input)
            if book is None:
                st.error(f"ISBN {isbn_input} not found on Open Library.")
            elif insert_book(book):
                st.success(f"Saved: {book['title']} by {book['author']}")
            else:
                st.info(f"Already in library: {book['title']}")

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(
    "SELECT title, author, genre, language, publication_year, isbn, cover_url FROM books ORDER BY title",
    conn,
)
conn.close()

# --- Filters ---
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    query = st.text_input("Search by title or author")

with col2:
    languages = ["All"] + sorted(df["language"].dropna().unique().tolist())
    language_choice = st.selectbox("Language", languages)

with col3:
    genres = ["All"] + sorted(df["genre"].dropna().unique().tolist())
    genre_choice = st.selectbox("Genre", genres)

filtered = df.copy()

if query:
    mask = (
        filtered["title"].str.contains(query, case=False, na=False)
        | filtered["author"].str.contains(query, case=False, na=False)
    )
    filtered = filtered[mask]

if language_choice != "All":
    filtered = filtered[filtered["language"] == language_choice]

if genre_choice != "All":
    filtered = filtered[filtered["genre"] == genre_choice]

# --- Results ---
view_mode = st.radio("View", ["Grid", "Table"], horizontal=True, label_visibility="collapsed")
st.write(f"{len(filtered)} of {len(df)} book(s) shown")

if view_mode == "Table":
    st.dataframe(filtered.drop(columns=["cover_url"]), width="stretch", hide_index=True)
else:
    render_grid(filtered)
