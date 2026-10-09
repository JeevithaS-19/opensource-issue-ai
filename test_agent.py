import json
from unittest.mock import patch

from agent import analyze_bug_report


def run_with_mock(title, description, mock_response):
    with patch(
        "agent.generate_response",
        return_value=json.dumps(mock_response),
    ):
        return analyze_bug_report(title, description)


def test_valid_report():
    mock_response = {
        "summary": "Login fails when valid credentials are used.",
        "category": "Authentication",
        "priority": "Medium",
        "missing_information": ["Which browser are you using?"],
        "labels": ["bug", "login"],
    }

    result = run_with_mock(
        "Login fails",
        "Users cannot log in with valid credentials.",
        mock_response,
    )

    assert result["summary"] == mock_response["summary"]
    assert result["category"] == "Authentication"
    assert result["priority"] == "Medium"
    assert isinstance(result["missing_information"], list)
    assert isinstance(result["labels"], list)

    assert set(result.keys()) == {
        "summary",
        "category",
        "priority",
        "missing_information",
        "labels",
    }

    print("PASS: Valid bug report.")


def test_empty_title_rejected():
    try:
        analyze_bug_report("", "Login fails")
    except ValueError:
        print("PASS: Empty title rejected.")
        return

    raise AssertionError("Empty title should have been rejected.")


def test_empty_description_rejected():
    try:
        analyze_bug_report("Login fails", "")
    except ValueError:
        print("PASS: Empty description rejected.")
        return

    raise AssertionError(
        "Empty description should have been rejected."
    )


def test_invalid_priority_rejected():
    mock_response = {
        "summary": "Login fails.",
        "category": "Authentication",
        "priority": "Urgent",
        "missing_information": [],
        "labels": ["login"],
    }

    try:
        run_with_mock(
            "Login fails",
            "Users cannot log in.",
            mock_response,
        )
    except ValueError:
        print("PASS: Invalid priority rejected.")
        return

    raise AssertionError(
        "Invalid priority should have been rejected."
    )


if __name__ == "__main__":
    test_valid_report()
    test_empty_title_rejected()
    test_empty_description_rejected()
    test_invalid_priority_rejected()

    print("\nAll four basic tests passed!")