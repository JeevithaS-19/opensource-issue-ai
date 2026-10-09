from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def find_similar_issues(new_report, existing_issues, threshold=0.25):
    """
    Find potentially similar issue reports.

    Returns matches sorted by similarity, highest first.
    Similarity is a clue for human review, not proof of a duplicate.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")
    if not existing_issues:
        return []

    new_text = (
        str(new_report.get("title", "")) + " " +
        str(new_report.get("description", ""))
    ).strip()

    if not new_text:
        return []

    valid_issues = []
    existing_texts = []

    for issue in existing_issues:
        text = (
            str(issue.get("title", "")) + " " +
            str(issue.get("description", ""))
        ).strip()
        if text:
            valid_issues.append(issue)
            existing_texts.append(text)

    if not existing_texts:
        return []

    documents = [new_text] + existing_texts

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2)
        )
        vectors = vectorizer.fit_transform(documents)
    except ValueError:
        # Empty vocabulary, such as reports containing only stop words.
        return []
    scores = cosine_similarity(
        vectors[0:1],
        vectors[1:]
    ).flatten()

    matches = []

    for issue, score in zip(valid_issues, scores):
        score = float(score)

        if score >= threshold:
            matches.append({
                "id": issue.get("id"),
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "similarity": round(score, 3)
            })
    matches.sort(
        key=lambda match: match["similarity"],
        reverse=True
    )

    return matches
