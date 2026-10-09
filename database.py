
import json
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
                missing_info TEXT DEFAULT '[]',
                labels TEXT DEFAULT '[]',
                duplicate_of INTEGER,
                status TEXT DEFAULT 'Pending Review',
                created_at TEXT NOT NULL
            )
        """)


def _decode_list(value):
    """Decode JSON lists, while supporting older saved Python-list strings."""
    if isinstance(value, list):
        return value

    if not value:
        return []

    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Compatibility with older records saved using str(list).
    import ast
    try:
        result = ast.literal_eval(value)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def _format_issue(row):
    """Convert a database row to a dictionary with lists decoded."""
    if row is None:
        return None

    issue = dict(row)
    issue["missing_info"] = _decode_list(issue.get("missing_info"))
    issue["missing_information"] = issue["missing_info"]
    issue["labels"] = _decode_list(issue.get("labels"))
    return issue


def save_issue(issue_data):
    """Save an issue and return its database ID."""
    title = str(issue_data.get("title", "")).strip()
    description = str(issue_data.get("description", "")).strip()

    if not title or not description:
        raise ValueError("Issue title and description are required.")

    # Accept either field name from the AI agent or frontend.
    missing_questions = issue_data.get("missing_information")
    if missing_questions is None:
        missing_questions = issue_data.get("missing_info", [])

    if missing_questions is None:
        missing_questions = []
    elif not isinstance(missing_questions, list):
        missing_questions = [str(missing_questions)]

    labels = issue_data.get("labels", [])
    if labels is None:
        labels = []
    elif not isinstance(labels, list):
        labels = [str(labels)]

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
            INSERT INTO issues (
                title, description, category, priority,
                summary, missing_info, labels, duplicate_of,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            description,
            issue_data.get("category", "Unknown"),
            issue_data.get("priority", "Needs review"),
            issue_data.get("summary", ""),
            json.dumps(missing_questions, ensure_ascii=False),
            json.dumps(labels, ensure_ascii=False),
            issue_data.get("duplicate_of"),
            issue_data.get("status", "Pending Review"),
            datetime.now().isoformat(timespec="seconds")
        ))
        return cursor.lastrowid


def get_all_issues():
    """Return all issues, newest first."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM issues ORDER BY id DESC"
        ).fetchall()
        return [_format_issue(row) for row in rows]


def get_issue_by_id(issue_id):
    """Return one issue by ID, or None if it does not exist."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,)
        ).fetchone()
        return _format_issue(row)


def update_issue_status(issue_id, status):
    """Update an issue's status. Return True if the issue exists."""
    allowed_statuses = {
        "Pending Review",
        "Approved",
        "Rejected",
        "Duplicate"
    }

    if status not in allowed_statuses:
        raise ValueError(
            f"Invalid status. Choose one of: {sorted(allowed_statuses)}"
        )

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            "UPDATE issues SET status = ? WHERE id = ?",
            (status, issue_id)
        )
        return cursor.rowcount > 0


def delete_issue(issue_id):
    """Delete an issue by ID. Return True if it existed."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            "DELETE FROM issues WHERE id = ?",
            (issue_id,)
        )
        return cursor.rowcount > 0
