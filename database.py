
import sqlite3
from datetime import datetime

DB_NAME = "issues.db"


def initialize_database():
    """Create the issues table if it does not exist."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'Unknown',
                priority TEXT DEFAULT 'Needs review',
                summary TEXT DEFAULT '',
                missing_info TEXT DEFAULT '',
                labels TEXT DEFAULT '',
                duplicate_of INTEGER,
                status TEXT DEFAULT 'Pending Review',
                created_at TEXT NOT NULL
            )
        """)


def save_issue(issue_data):
    """Save an issue and return its database ID."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
            INSERT INTO issues (
                title, description, category, priority,
                summary, missing_info, labels, duplicate_of,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue_data["title"],
            issue_data["description"],
            issue_data.get("category", "Unknown"),
            issue_data.get("priority", "Needs review"),
            issue_data.get("summary", ""),
            str(issue_data.get("missing_info", [])),
            str(issue_data.get("labels", [])),
            issue_data.get("duplicate_of"),
            issue_data.get("status", "Pending Review"),
            datetime.now().isoformat(timespec="seconds")
        ))
        return cursor.lastrowid


def get_all_issues():
    """Return all saved issues, newest first."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM issues ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_issue_by_id(issue_id):
    """Return one issue by ID, or None if not found."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_issue(issue_id):
    """Delete an issue by ID."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            "DELETE FROM issues WHERE id = ?",
            (issue_id,)
        )
        return cursor.rowcount > 0
