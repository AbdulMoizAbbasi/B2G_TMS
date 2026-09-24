from tender_scraper.relevance.keyword_matcher import find_keyword_matches


def calculate_relevance_score(text):
    """
    Calculate tender relevance using keyword matching only.

    Scoring:
        Each unique matched keyword = 10 points.

    Capabilities:
        Capabilities are determined from the matched keywords.
        A keyword may belong to multiple capabilities.

    No semantic matching is used.
    No classification is used.

    Returns:
    {
        "keyword_score": int,
        "matched_keywords": [...],
        "matched_capabilities": [...]
    }
    """

    # -------------------------
    # Empty text
    # -------------------------

    if not text or not str(text).strip():
        return {
            "keyword_score": 0,
            "matched_keywords": [],
            "matched_capabilities": [],
        }

    # -------------------------
    # Keyword matching
    # -------------------------

    keyword_result = find_keyword_matches(text)

    keyword_score = keyword_result["keyword_score"]
    matched_keywords = keyword_result["matched_keywords"]

    capability_matches = keyword_result.get(
        "capability_matches",
        {},
    )

    # -------------------------
    # Matched capabilities
    # -------------------------

    matched_capabilities = list(
        capability_matches.keys()
    )

    return {
        "keyword_score": keyword_score,
        "matched_keywords": matched_keywords,
        "matched_capabilities": matched_capabilities,
    }


if __name__ == "__main__":

    test_cases = [
        # ==========================================
        # MULTIPLE KEYWORDS
        # ==========================================

        "Procurement of SIM Cards and M2M Connectivity",
        "Provision of Internet Broadband Connectivity",
        "Procurement of Fiber Optic Cable and Network Equipment",
        "Supply of Firewall and Network Security Appliances",
        "Procurement of Cloud Computing and Virtual Data Center Services",
        "Supply of Servers, Storage and Hyper-Converged Infrastructure",
        "Procurement of GPU Servers for Artificial Intelligence Computing",
        "Enterprise ERP Software Implementation and Licensing",

        # ==========================================
        # SINGLE KEYWORD
        # ==========================================

        "Provision of Enterprise Network Infrastructure",
        "Supply and Installation of Information Technology Hardware",
        "Development and Implementation of Enterprise Management System",

        # ==========================================
        # NO KEYWORDS
        # ==========================================

        "Purchase of IT Equipment for Government Offices",
        "Procurement of Poultry Feed and One Day Old Chicks",
        "Construction of Boundary Wall and Renovation Works",
        "Supply of Office Furniture and Chairs",
        "Procurement of Laboratory Chemicals and Glassware",
        "Purchase of Medical Equipment for District Hospital",
        "Procurement of School Uniforms and Sports Equipment",

        # ==========================================
        # FALSE-POSITIVE TYPE CASES
        # ==========================================

        "Cold Storage Services",
        "63 GSM Paper",
    ]

    print("\nRelevance Scorer Tests")
    print("======================")

    for text in test_cases:

        result = calculate_relevance_score(text)

        print("\nTender:", text)

        print(
            "Matched keywords:",
            result["matched_keywords"],
        )

        print(
            "Keyword score:",
            result["keyword_score"],
        )

        print(
            "Matched capabilities:",
            result["matched_capabilities"],
        )