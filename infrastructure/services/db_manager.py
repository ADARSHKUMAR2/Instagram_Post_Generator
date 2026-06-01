import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Save the DB in a mounted volume so it survives container restarts
        self.db_path = os.getenv("DB_PATH", "/app/infrastructure/queue.db")
        self._init_db()

    def _init_db(self):
        """Creates the queue table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS post_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL, -- 'drive' or 'pollinations'
                    file_id_or_url TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    scheduled_time DATETIME NOT NULL,
                    status TEXT DEFAULT 'pending' -- 'pending', 'processing', 'completed', 'failed'
                )
            """)
            conn.commit()

    def add_to_queue(self, source_type: str, file_id_or_url: str, caption: str, scheduled_time: datetime):
        """Adds a new post to the publishing queue."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO post_queue (source_type, file_id_or_url, caption, scheduled_time)
                VALUES (?, ?, ?, ?)
            """, (source_type, file_id_or_url, caption, scheduled_time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return cursor.lastrowid

    def get_pending_posts(self):
        """Fetches posts that are scheduled for now or in the past but haven't run yet."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM post_queue 
                WHERE status = 'pending' AND scheduled_time <= ?
            """, (now,))
            return [dict(row) for row in cursor.fetchall()]

    def update_status(self, post_id: int, new_status: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE post_queue SET status = ? WHERE id = ?", (new_status, post_id))
            conn.commit()