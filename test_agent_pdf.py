import json
from unittest.mock import patch

from agent import analyze_bug_report


def test_pdf_crash_report():
    mock_response = {
        "summary": (
            "Uploading a PDF larger than 10 MB closes "
            "the application on Windows."
        ),
        "category": "Upload",
        "priority": "High",
        "missing_information": [
            "Which application version is being used?",
            "Do smaller PDFs upload successfully?",
            "Does an error message appear?",
        ],
        "labels": ["bug", "pdf", "upload", "windows"],
    }

    with patch(
        "agent.generate_response",
        return_value=json.dumps(mock_response),
    ):
        result = analyze_bug_report(
            "PDF upload crashes",
            (
                "Uploading a PDF larger than 10 MB "
                "closes the application on Windows."
            ),
        )

    assert result["category"] == "Upload"
    assert result["priority"] == "High"
    assert "10 MB" in result["summary"]
    assert "Windows" in result["summary"]
    assert len(result["missing_information"]) > 0

    print("PASS: PDF crash report is preserved.")


if __name__ == "__main__":
    test_pdf_crash_report()
    print("\nPDF regression test passed!")