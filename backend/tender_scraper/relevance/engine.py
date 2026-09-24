from tender_scraper.relevance.text_builder import build_tender_text

from tender_scraper.relevance.scorer import calculate_relevance_score


def analyze_tender(tender):
    """
    Analyze one tender for business relevance.

    Returns the original tender data together with
    relevance analysis.
    """

    tender_text = build_tender_text(tender)

    relevance = calculate_relevance_score(
        tender_text
    )

    return {
        "tender": tender,
        "relevance": relevance,
    }