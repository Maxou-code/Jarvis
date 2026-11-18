from contextlib import contextmanager
import json
import sqlite3
import time
import uuid


class ConversationStore:
    def __init__(self, path):
        self.path = str(path)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    title_locked INTEGER NOT NULL DEFAULT 0
                )
            """)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(conversations)")
            }
            if "title_locked" not in columns:
                connection.execute(
                    "ALTER TABLE conversations ADD COLUMN title_locked "
                    "INTEGER NOT NULL DEFAULT 0"
                )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self):
        conversation = {
            "id": str(uuid.uuid4()),
            "title": "Nouvelle conversation",
            "messages": [],
        }
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations (id, title, messages, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (conversation["id"], conversation["title"], "[]", now, now),
            )
        return conversation

    def list_conversations(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, updated_at FROM conversations "
                "WHERE messages != '[]' ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, conversation_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, title, messages FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "messages": json.loads(row["messages"]),
        }

    def rename(self, conversation_id, title):
        title = title.strip()
        if not title:
            raise ValueError("Le nom de la conversation ne peut pas être vide.")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE conversations SET title = ?, title_locked = 1, updated_at = ? "
                "WHERE id = ?",
                (title[:120], time.time(), conversation_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Conversation introuvable : {conversation_id}")
        return title[:120]

    def delete(self, conversation_id):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Conversation introuvable : {conversation_id}")

    def save(self, conversation):
        messages = [
            dict(message)
            for message in conversation["messages"]
            if message.get("role") in {
                "user", "assistant", "thinking", "system", "chart", "model3d"
            }
        ]
        first_user_message = next(
            (message["content"].strip() for message in messages
             if message["role"] == "user" and message["content"].strip()),
            "",
        )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT title, title_locked FROM conversations WHERE id = ?",
                (conversation["id"],),
            ).fetchone()
            if row is None:
                raise KeyError(f"Conversation introuvable : {conversation['id']}")
            title = row["title"] if row["title_locked"] else (
                first_user_message.replace("\n", " ")[:48] or "Nouvelle conversation"
            )
            connection.execute(
                "UPDATE conversations SET title = ?, messages = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    title,
                    json.dumps(messages, ensure_ascii=False),
                    time.time(),
                    conversation["id"],
                ),
            )
        conversation["title"] = title
        conversation["messages"] = messages
