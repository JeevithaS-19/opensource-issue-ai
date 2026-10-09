
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

        issue_id = database.save_issue({
            "title": "Application crashes on login",
            "description": (
                "The application crashes whenever "
                "I enter my username and password."
            ),
            "category": "Bug",
            "priority": "High",
            "labels": ["bug", "login"]
        })

        existing = database.get_all_issues()

        new_report = {
            "title": "Application crashes on login",
            "description": (
                "The application crashes whenever "
                "I enter my username and password."
            )
        }

        matches = find_similar_issues(
            new_report,
            existing,
            threshold=0.15
        )

        print("Saved issue ID:", issue_id)
        print("Number of saved issues:", len(existing))
        print("Potential duplicate matches:")

        for match in matches:
            print(
                f"ID: {match['id']} | "
                f"Title: {match['title']} | "
                f"Similarity: {match['similarity']}"
            )

        assert len(existing) == 1, "Issue was not saved correctly."
        assert matches, "Expected to find the matching issue."

        print("\nAll tests passed!")

    finally:
        # Restore the original database setting.
        database.DB_NAME = original_db

        # Remove temporary files after SQLite connections are closed.
        try:
            os.remove(test_db)
            os.rmdir(temp_dir)
        except PermissionError:
            print("Test database cleanup can be done manually.")
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
