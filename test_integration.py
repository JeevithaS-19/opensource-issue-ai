import json
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import database
import server


def request_json(url, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, json.loads(payload) if payload else None


def main():
    with tempfile.TemporaryDirectory(prefix="buglens_test_") as tmp:
        original_db = database.DB_NAME
        database.DB_NAME = str(Path(tmp) / "test.db")
        httpd = None
        thread = None
        try:
            httpd = server.create_server(port=0, initialize_db=True)
            port = httpd.server_address[1]
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{port}"
            time.sleep(0.05)
            assert request_json(base + "/api/health")[0] == 200
            with urlopen(base + "/", timeout=5) as response:
                code = response.status
                page = response.read().decode("utf-8")
            assert code == 200 and "BugLens" in page
            assert request_json(base + "/api/issues") == (200, [])

            status, saved = request_json(base + "/api/issues", "POST", {
                "title": "Login button does not respond", "description": "Clicking login does nothing.",
                "category": "Authentication", "priority": "Medium", "summary": "Login does not respond",
                "missing_info": "Browser and version; error message", "labels": "bug, login",
                "status": "Approved", "duplicate_of": None,
            })
            assert status == 201, saved
            assert saved["missing_info"] == ["Browser and version", "error message"]
            assert saved["missing_information"] == saved["missing_info"]
            assert saved["labels"] == ["bug", "login"]

            mock_analysis = {"summary": "Login action fails", "category": "Authentication", "priority": "Medium",
                             "missing_information": ["Which browser?"], "labels": ["bug", "authentication"]}
            with patch("server.analyze_bug_report", return_value=mock_analysis):
                status, result = request_json(base + "/api/analyze", "POST", {
                    "title": "Login button does not respond", "description": "Clicking login does nothing.",
                    "expected": "Login should succeed", "actual": "Nothing happens",
                })
            assert status == 200, result
            assert result["missing_info"] == ["Which browser?"]
            assert result["duplicates"] and result["duplicates"][0]["id"] == saved["id"]
            assert 0.25 <= result["duplicates"][0]["score"] <= 1.0
            assert "issue_draft" in result and result["component"] == "Authentication"

            status, updated = request_json(base + f"/api/issues/{saved['id']}/status", "PATCH", {"status": "Rejected"})
            assert status == 200 and updated["status"] == "Rejected"
            assert request_json(base + "/api/analyze", "POST", {"title": "", "description": "desc"})[0] == 400
            assert request_json(base + "/api/issues", "POST", {"title": None, "description": "desc"})[0] == 400
            print("All integration API tests passed.")
        finally:
            if httpd is not None:
                httpd.shutdown()
                httpd.server_close()
            if thread is not None:
                thread.join(timeout=1)
            database.DB_NAME = original_db


if __name__ == "__main__":
    main()
