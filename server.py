"""Standard-library HTTP bridge connecting BugLens to AI and SQLite modules."""
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import re
import sys

import database
from agent import analyze_bug_report
from duplicate_detector import find_similar_issues

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_STATUSES = {"Pending Review", "Approved", "Rejected", "Duplicate"}


def _as_list(value, separators=",;"):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return [str(value)] if str(value).strip() else []
    text = value.strip()
    if not text:
        return []
    pattern = "[" + re.escape(separators) + "]+"
    return [item.strip() for item in re.split(pattern, text) if item.strip()]


def _error(message, status=400):
    return {"error": message}, status


def analyze_payload(payload):
    if not isinstance(payload, dict):
        return _error("Request body must be a JSON object.")
    title, description = payload.get("title"), payload.get("description")
    if not isinstance(title, str) or not title.strip():
        return _error("Bug title is required.")
    if not isinstance(description, str) or not description.strip():
        return _error("Bug description is required.")
    expected, actual = payload.get("expected", ""), payload.get("actual", "")
    analysis_description = description.strip()
    if isinstance(expected, str) and expected.strip():
        analysis_description += "\nExpected behavior: " + expected.strip()
    if isinstance(actual, str) and actual.strip():
        analysis_description += "\nActual behavior: " + actual.strip()
    try:
        analysis = analyze_bug_report(title.strip(), analysis_description)
        current_issues = database.get_all_issues()
        matches = find_similar_issues(
            {"title": title.strip(), "description": analysis_description}, current_issues
        )
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception:
        print("Bug analysis failed:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return _error("Analysis failed. Check that the model service is running and inspect the server output.", 502)

    missing = analysis.get("missing_information", [])
    labels = analysis.get("labels", [])
    category = analysis.get("category", "Other")
    draft = (
        f"Title: {title.strip()}\n\n"
        f"Summary: {analysis.get('summary', '')}\n\n"
        f"Description: {description.strip()}\n\n"
        f"Expected behavior: {expected.strip() if isinstance(expected, str) and expected.strip() else 'Not provided'}\n"
        f"Actual behavior: {actual.strip() if isinstance(actual, str) and actual.strip() else 'Not provided'}\n\n"
        "Missing information:\n"
        + ("\n".join(f"- {item}" for item in missing) if missing else "- None identified")
        + "\n\nSuggested labels: " + ", ".join(labels)
        + f"\nSuggested priority: {analysis.get('priority', 'Unknown')} (AI suggestion, needs review)"
    )
    return ({
        "summary": analysis.get("summary", ""),
        "category": category,
        "component": analysis.get("component") or category,
        "priority": analysis.get("priority", "Unknown"),
        "labels": labels,
        "missing_info": missing,
        "issue_draft": draft,
        "duplicates": [
            {"id": match.get("id"), "title": match.get("title", ""), "score": match.get("similarity", 0.0)}
            for match in matches
        ],
    }, 200)


def create_issue_payload(payload):
    if not isinstance(payload, dict):
        return _error("Request body must be a JSON object.")
    title, description = payload.get("title"), payload.get("description")
    if not isinstance(title, str) or not title.strip():
        return _error("Issue title is required.")
    if not isinstance(description, str) or not description.strip():
        return _error("Issue description is required.")
    status = payload.get("status", "Pending Review")
    if status not in ALLOWED_STATUSES:
        return _error(f"Invalid status: {status}")
    issue_data = dict(payload)
    issue_data["title"] = title.strip()
    issue_data["description"] = description.strip()
    issue_data["missing_information"] = _as_list(
        payload.get("missing_information", payload.get("missing_info", [])), ";\n"
    )
    issue_data["labels"] = _as_list(payload.get("labels", []), ",;\n")
    issue_data["status"] = status
    try:
        issue_id = database.save_issue(issue_data)
        saved = database.get_issue_by_id(issue_id)
    except ValueError as exc:
        return _error(str(exc), 400)
    return saved, 201


class BugLensHandler(BaseHTTPRequestHandler):
    server_version = "BugLensHTTP/1.0"

    def _send(self, body, status=200, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            encoded = body.encode("utf-8")
        else:
            encoded = b""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, "Invalid Content-Length."
        if length <= 0 or length > 1024 * 1024:
            return None, "Request body is empty or exceeds 1 MB."
        try:
            return json.loads(self.rfile.read(length).decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, "Request body must contain valid JSON."

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            try:
                self._send((BASE_DIR / "index.html").read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
            except OSError:
                self._send("Frontend file not found.", 404, "text/plain; charset=utf-8")
        elif path == "/api/health":
            self._send({"ok": True, "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b")})
        elif path == "/api/issues":
            self._send(database.get_all_issues())
        else:
            self._send({"error": "Not found."}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload, error = self._read_json()
        if error:
            self._send({"error": error}, 400)
            return
        if path == "/api/analyze":
            body, status = analyze_payload(payload)
            self._send(body, status)
        elif path == "/api/issues":
            body, status = create_issue_payload(payload)
            self._send(body, status)
        else:
            self._send({"error": "Not found."}, 404)

    def do_PATCH(self):
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/issues/(\d+)/status", path)
        if not match:
            self._send({"error": "Not found."}, 404)
            return
        payload, error = self._read_json()
        if error:
            self._send({"error": error}, 400)
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
            self._send({"error": "Provide a JSON object with a status field."}, 400)
            return
        issue_id = int(match.group(1))
        try:
            updated = database.update_issue_status(issue_id, payload["status"])
        except ValueError as exc:
            self._send({"error": str(exc)}, 400)
            return
        if not updated:
            self._send({"error": "Issue not found."}, 404)
            return
        self._send(database.get_issue_by_id(issue_id))

    def log_message(self, fmt, *args):
        # Keep routine request logging concise while still showing server activity.
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def create_server(host="127.0.0.1", port=5000, initialize_db=True):
    if initialize_db:
        database.initialize_database()
    return ThreadingHTTPServer((host, port), BugLensHandler)


if __name__ == "__main__":
    httpd = create_server()
    print("BugLens backend running at http://127.0.0.1:5000")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down BugLens.")
    finally:
        httpd.server_close()
