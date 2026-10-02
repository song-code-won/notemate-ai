"""
Note CRUD and search service for NoteMate AI.
"""

from typing import List, Optional
from app.database import get_db_connection, current_iso_time
from app.models import NoteResponse, NoteCreate, NoteUpdate


def dict_from_row(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": row["tags"] or "",
        "summary": row["summary"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class NoteService:
    @staticmethod
    def create_note(data: NoteCreate) -> NoteResponse:
        now = current_iso_time()
        tags_str = data.tags.strip() if data.tags else ""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notes (title, content, tags, summary, created_at, updated_at)
                VALUES (?, ?, ?, '', ?, ?)
                """,
                (data.title.strip(), data.content, tags_str, now, now),
            )
            note_id = cursor.lastrowid
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return NoteResponse(**dict_from_row(row))

    @staticmethod
    def get_note(note_id: int) -> Optional[NoteResponse]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return NoteResponse(**dict_from_row(row))

    @staticmethod
    def list_notes(search_query: Optional[str] = None, tag: Optional[str] = None) -> List[NoteResponse]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM notes"
            params = []
            conditions = []

            if search_query and search_query.strip():
                q = f"%{search_query.strip()}%"
                conditions.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
                params.extend([q, q, q])

            if tag and tag.strip():
                t = f"%{tag.strip()}%"
                conditions.append("tags LIKE ?")
                params.append(t)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY updated_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [NoteResponse(**dict_from_row(r)) for r in rows]

    @staticmethod
    def update_note(note_id: int, data: NoteUpdate) -> Optional[NoteResponse]:
        now = current_iso_time()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if not row:
                return None

            current_data = dict_from_row(row)
            new_title = data.title.strip() if data.title is not None else current_data["title"]
            new_content = data.content if data.content is not None else current_data["content"]
            new_tags = data.tags.strip() if data.tags is not None else current_data["tags"]
            new_summary = data.summary if data.summary is not None else current_data["summary"]

            cursor.execute(
                """
                UPDATE notes
                SET title = ?, content = ?, tags = ?, summary = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, new_content, new_tags, new_summary, now, note_id),
            )
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            updated_row = cursor.fetchone()
            return NoteResponse(**dict_from_row(updated_row))

    @staticmethod
    def delete_note(note_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM notes WHERE id = ?", (note_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return True
