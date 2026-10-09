
import os
import tempfile

import database
from duplicate_detector import find_similar_issues


def main():
    original_db = database.DB_NAME
    temp_dir = tempfile.mkdtemp(prefix="issue_test_")
    test_db = os.path.join(temp_dir, "test_issues.db")

    try:
        database.DB_NAME = test_db
        database.initialize_database()

        # Test saving AI output using missing_information.
        issue_id = database.save_issue({
            "title": "Application crashes on login",
            "description": (
                "The application crashes whenever I enter "
                "my username and password."
            ),
            "category": "Bug",
            "priority": "High",
            "summary": "Application crashes during login.",
            "missing_information": [
                "Which operating system are you using?",
                "What application version is installed?"
            ],
            "labels": ["bug", "login"]
        })

        saved = database.get_issue_by_id(issue_id)

        assert saved is not None
        assert saved["missing_info"] == [
            "Which operating system are you using?",
            "What application version is installed?"
        ]
        assert saved["missing_information"] == saved["missing_info"]
        assert saved["labels"] == ["bug", "login"]
        print("PASS: Database saving and JSON list fields")

        # Test compatibility with the older field name.
        second_id = database.save_issue({
            "title": "Settings page freezes",
            "description": "The settings page stops responding.",
            "missing_info": ["Which settings page?"]
        })

        second = database.get_issue_by_id(second_id)

        assert second["missing_info"] == ["Which settings page?"]
        print("PASS: Backward-compatible missing_info field")

        # Test status updates.
        assert database.update_issue_status(issue_id, "Approved")
        assert database.get_issue_by_id(issue_id)["status"] == "Approved"
        assert not database.update_issue_status(99999, "Approved")
        print("PASS: Issue status updates")

        # Test invalid title and description validation.
        invalid_issues = [
            {"title": None, "description": "Valid description"},
            {"title": "Valid title", "description": None},
            {"title": "", "description": "Valid description"},
            {"title": "Valid title", "description": ""},
            {"title": "   ", "description": "Valid description"},
            {"title": "Valid title", "description": "   "},
            {"title": 123, "description": "Valid description"},
            {"title": "Valid title", "description": ["not", "text"]},
        ]

        for issue in invalid_issues:
            try:
                database.save_issue(issue)
            except ValueError:
                pass
            else:
                raise AssertionError(
                    f"Invalid issue should have been rejected: {issue}"
                )

        print("PASS: Invalid title and description validation")

        # Confirm valid values are trimmed and saved.
        trimmed_id = database.save_issue({
            "title": "  Login crash  ",
            "description": "  App crashes on login  "
        })

        trimmed = database.get_issue_by_id(trimmed_id)
        assert trimmed["title"] == "Login crash"
        assert trimmed["description"] == "App crashes on login"
        print("PASS: Valid title and description are trimmed")

        # Test duplicate detection with different but overlapping wording.
        existing = database.get_all_issues()

        new_report = {
            "title": "Login application crashes",
            "description": (
                "The application crashes when entering "
                "the username and password."
            )
        }

        matches = find_similar_issues(
            new_report,
            existing,
            threshold=0.15
        )

        assert matches, "Expected a potentially similar report."
        assert matches[0]["id"] == issue_id

        print(
            "PASS: Similar report found with score",
            matches[0]["similarity"]
        )

        # Test an unrelated report.
        unrelated_report = {
            "title": "PDF upload fails",
            "description": (
                "Uploading a PDF document produces an error."
            )
        }

        unrelated_matches = find_similar_issues(
            unrelated_report,
            existing,
            threshold=0.25
        )

        assert not unrelated_matches, (
            "Unexpected match for unrelated PDF report."
        )
        print("PASS: Unrelated report not matched")

        # Test empty input cases.
        assert find_similar_issues(new_report, []) == []
        assert find_similar_issues(
            {"title": "", "description": ""},
            existing
        ) == []
        print("PASS: Empty input handling")

        # Test delete.
        assert database.delete_issue(second_id)
        assert database.get_issue_by_id(second_id) is None
        print("PASS: Issue deletion")

        print("\nAll tests passed!")

    finally:
        database.DB_NAME = original_db

        # Attempt to remove temporary SQLite files.
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = test_db + suffix
            try:
                if os.path.exists(path):
                    os.remove(path)
            except PermissionError:
                print("Could not remove temporary file:", path)

        try:
            os.rmdir(temp_dir)
        except OSError:
            print("Temporary folder could not be removed:", temp_dir)


if __name__ == "__main__":
    main()
