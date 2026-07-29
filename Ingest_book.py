"""
ingest_book.py

Step 1 of the home library project: given an ISBN, fetch book metadata
from Open Library and insert it into a local SQLite database.

Usage:
    python ingest_book.py 9780140449136
    python ingest_book.py 9780140449136 9782070368228 9789953890001

No API key required — Open Library's ISBN/Works/Authors endpoints are public.
"""

import sqlite3
import sys
import requests

DB_PATH = "library.db"
OPEN_LIBRARY_BASE = "https://openlibrary.org"


def create_db(db_path: str = DB_PATH) -> None:
    """Create the books table if it doesn't already exist."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT UNIQUE,
            title TEXT,
            author TEXT,
            genre TEXT,
            publication_year TEXT,
            language TEXT,
            cover_url TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_book_data(isbn: str) -> dict | None:
    """
    Fetch metadata for a single ISBN from Open Library.
    Returns a dict of cleaned fields, or None if the book isn't found.
    """
    isbn = isbn.strip().replace("-", "")
    resp = requests.get(f"{OPEN_LIBRARY_BASE}/isbn/{isbn}.json", timeout=10)

    if resp.status_code != 200:
        return None

    data = resp.json()

    title = data.get("title", "Unknown title")
    publish_date = data.get("publish_date", "Unknown")
    languages = data.get("languages", [])
    language = languages[0]["key"].split("/")[-1] if languages else "und"

    # Author names require a follow-up request — the ISBN record only has keys.
    author_names = []
    for author_ref in data.get("authors", []):
        author_key = author_ref.get("key")
        if not author_key:
            continue
        a_resp = requests.get(f"{OPEN_LIBRARY_BASE}{author_key}.json", timeout=10)
        if a_resp.status_code == 200:
            author_names.append(a_resp.json().get("name", "Unknown author"))
    author = ", ".join(author_names) if author_names else "Unknown author"

    # Genre/subject data lives on the parent "work" record, not the ISBN record.
    genre = "Unclassified"
    works = data.get("works", [])
    if works:
        work_key = works[0].get("key")
        w_resp = requests.get(f"{OPEN_LIBRARY_BASE}{work_key}.json", timeout=10)
        if w_resp.status_code == 200:
            subjects = w_resp.json().get("subjects", [])
            if subjects:
                genre = subjects[0]  # first listed subject as a simple genre stand-in

    cover_ids = data.get("covers", [])
    cover_url = (
        f"https://covers.openlibrary.org/b/id/{cover_ids[0]}-M.jpg" if cover_ids else ""
    )

    return {
        "isbn": isbn,
        "title": title,
        "author": author,
        "genre": genre,
        "publication_year": publish_date,
        "language": language,
        "cover_url": cover_url,
    }


def insert_book(book: dict, db_path: str = DB_PATH) -> None:
    """Insert a book dict into the database. Skips silently if ISBN already exists."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO books (isbn, title, author, genre, publication_year, language, cover_url)
            VALUES (:isbn, :title, :author, :genre, :publication_year, :language, :cover_url)
            """,
            book,
        )
        conn.commit()
        print(f"  -> saved: {book['title']} by {book['author']}")
    except sqlite3.IntegrityError:
        print(f"  -> already in database (ISBN {book['isbn']}), skipped")
    finally:
        conn.close()


def main(isbns: list[str]) -> None:
    create_db()
    for isbn in isbns:
        print(f"Fetching {isbn}...")
        book = fetch_book_data(isbn)
        if book is None:
            print(f"  -> not found on Open Library, skipped (ISBN {isbn})")
            continue
        insert_book(book)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_book.py <isbn> [<isbn2> ...]")
        sys.exit(1)
    main(sys.argv[1:])