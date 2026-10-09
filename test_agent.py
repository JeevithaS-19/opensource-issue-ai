import json
from unittest.mock import patch
from agent import analyze_bug_report


def run_mock(title, description, response):
    with patch("agent.generate_response", return_value=json.dumps(response)):
        return analyze_bug_report(title, description)


def test_basic_validation():
    valid = {"summary": "Login fails", "category": "Authentication", "priority": "Medium",
             "missing_information": ["Which browser?"], "labels": ["bug", "login"]}
    result = run_mock("Login fails", "Clicking login does nothing", valid)
    assert set(result) == {"summary", "category", "priority", "missing_information", "labels"}
    for args in [("", "description"), ("title", "  ")]:
        try:
            analyze_bug_report(*args)
        except ValueError:
            pass
        else:
            raise AssertionError("Empty input was accepted")


def test_unsafe_credentials_are_sanitized():
    mock = {"summary": "Login fails", "category": "Authentication", "priority": "Medium",
            "missing_information": ["Please provide your password.", "Tell me your OTP.",
                                     "Share your API key.", "Which browser are you using?"],
            "labels": ["bug", "login", "password", "OTP", "API key"]}
    result = run_mock("Login fails", "User asks to request secrets", mock)
    joined = " ".join(result["missing_information"]).lower()
    assert "provide your password" not in joined and "tell me your otp" not in joined and "share your api key" not in joined
    assert any("error message or error code" in item.lower() for item in result["missing_information"])
    assert result["labels"] == ["bug", "login"]


def test_password_reset_report_preserved():
    mock = {"summary": "Password reset emails are not sent.", "category": "Authentication", "priority": "Medium",
            "missing_information": ["Which email provider is being used?", "Does the reset request show a success message?"],
            "labels": ["bug", "password-reset", "authentication"]}
    result = run_mock("Password reset emails are not sent", "Users never receive a reset email", mock)
    assert result["summary"] == mock["summary"]
    assert "password-reset" in result["labels"] and "authentication" in result["labels"]
    assert "Which email provider is being used?" in result["missing_information"]


if __name__ == "__main__":
    test_basic_validation()
    test_unsafe_credentials_are_sanitized()
    test_password_reset_report_preserved()
    print("All agent tests passed.")
