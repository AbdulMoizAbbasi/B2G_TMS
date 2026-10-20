
from tender_scraper.relevance.keyword_matcher import find_keyword_matches


def calculate_relevance_score(text):
    """
    Calculate tender relevance using keyword matching.

    Each unique retained keyword contributes its configured
    score from Keywords.

    Negative rules suppress individual keyword occurrences,
    not whole tenders or unrelated occurrences.
    """

    if not text or not str(text).strip():
        return {
            "keyword_score": 0,
            "matched_keywords": [],
            "matched_capabilities": [],
            "suppressed_matches": [],
        }

    keyword_result = find_keyword_matches(text)

    return {
        "keyword_score": keyword_result["keyword_score"],
        "matched_keywords": keyword_result["matched_keywords"],
        "matched_capabilities": list(
            keyword_result["capability_matches"].keys()
        ),
        "suppressed_matches": keyword_result.get(
            "suppressed_matches",
            [],
        ),
    }


if __name__ == "__main__":
    test_cases = [
        "Procurement of computer stationery",
        "Procurement of computer hardware",
        "Computer stationery and computer hardware",
        "Computer stationery and fiber connectivity",
        "Computer stationery and internet connectivity",
        "Cold Storage Services",
        "63 GSM Paper",
        "Computer numerical control grinding machine",
        "Computer hardware and CNC machine",
        "Fiber optic connectivity network",
        "Data storage system procurement",
        "Computer networking equipment",
        "GSM network equipment",
        "Cold storage facility and internet connectivity",
        "Computer stationery and computer networking equipment",
        "Procurement of fiber reels and fiber optic connectivity",
    ]

    for text in test_cases:
        result = calculate_relevance_score(text)

        print(f"\nTender: {text}")
        print("Score:", result["keyword_score"])
        print("Matched keywords:", result["matched_keywords"])
        print("Matched capabilities:", result["matched_capabilities"])
        print("Suppressed matches:", result["suppressed_matches"])
