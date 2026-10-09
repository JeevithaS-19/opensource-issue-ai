
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def find_similar_issues(new_report, existing_issues, threshold=0.25):
    """
    Find potentially similar issues.

    Returns a list sorted by similarity, highest first.
    A similarity score is a clue, not proof of a duplicate.
    """
    if not existing_issues:
        return []

    new_text = (
        str(new_report.get("title", "")) + " " +
        str(new_report.get("description", ""))
    ).strip()

    if not new_text:
        return []

    existing_texts = [
        (
            str(issue.get("title", "")) + " " +
            str(issue.get("description", ""))
        ).strip()
        for issue in existing_issues
    ]

    documents = [new_text] + existing_texts

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2)
        )
        vectors = vectorizer.fit_transform(documents)
    except ValueError:
        # Happens when all text is empty or contains no useful terms.
        return []

    scores = cosine_similarity(
        vectors[0:1], vectors[1:]
    ).flatten()

    matches = []

    for issue, score in zip(existing_issues, scores):
        if score >= threshold:
            matches.append({
                "id": issue.get("id"),
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "similarity": round(float(score), 3)
            })

    matches.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return matches
