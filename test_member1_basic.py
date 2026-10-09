import json
from unittest.mock import patch

from agent import analyze_bug_report


# Sample response for testing
sample_response = {
    "summary": "The login button does not respond after credentials are entered.",
    "category": "Authentication",
    "priority": "Medium",
    "missing_information": [
        "Which browser and operating system are being used?",
        "Does an error message appear?"
    ],
    "labels": ["bug", "login", "authentication"]
}


def fake_generate_response(prompt):
    """Return a sample response instead of calling a real AI."""
    return json.dumps(sample_response)


def test_valid_report():
    with patch("agent.generate_response", fake_generate_response):
        result = analyze_bug_report(
            "Login button not working",
            "Clicking Login after entering my credentials does nothing."
        )

    assert result["category"] == "Authentication"
    assert result["priority"] == "Medium"
    assert "missing_information" in result
    assert isinstance(result["labels"], list)

    print("PASS: Valid bug report")


def test_empty_title():
    try:
        analyze_bug_report("", "The application crashes.")

    except ValueError:
        print("PASS: Empty title rejected")

    else:
        raise AssertionError("Empty title was not rejected")


def test_empty_description():
    try:
        analyze_bug_report("Login button broken", "   ")

    except ValueError:
        print("PASS: Empty description rejected")

    else:
        raise AssertionError("Empty description was not rejected")


def test_invalid_priority():
    invalid_response = {
        "summary": "Login fails",
        "category": "Authentication",
        "priority": "Urgent",
        "missing_information": [],
        "labels": ["bug"]
    }

    with patch(
        "agent.generate_response",
        lambda prompt: json.dumps(invalid_response)
    ):
        try:
            analyze_bug_report("Login failure", "Login does not work.")

        except ValueError:
            print("PASS: Invalid priority rejected")

        else:
            raise AssertionError("Invalid priority was accepted")


if __name__ == "__main__":
    test_valid_report()
    test_empty_title()
    test_empty_description()
    test_invalid_priority()

    print("\nAll basic tests passed!")