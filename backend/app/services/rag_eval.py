import re


def normalize_terms(terms: list[str]) -> list[str]:
    return [term.strip().lower() for term in terms if term.strip()]


def evaluate_rag_answer(answer: str, citations: list[dict], expected_terms: list[str], min_citations: int = 1) -> dict:
    normalized_answer = answer.lower()
    terms = normalize_terms(expected_terms)
    matched_terms = [term for term in terms if re.search(rf"\b{re.escape(term)}\b", normalized_answer)]
    term_recall = len(matched_terms) / len(terms) if terms else 1.0
    citation_count = len(citations)
    missing_terms = [term for term in terms if term not in matched_terms]
    passed = term_recall >= 0.75 and citation_count >= min_citations
    return {
        "passed": passed,
        "term_recall": round(term_recall, 4),
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
        "citation_count": citation_count,
        "min_citations": min_citations,
    }
