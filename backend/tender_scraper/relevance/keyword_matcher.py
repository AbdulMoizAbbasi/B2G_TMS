import re
from tender_scraper.config.keywords import Keywords
from tender_scraper.config.capabilities import CAPABILITIES


def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def keyword_exists(text, keyword):
    pattern = rf"\b{re.escape(keyword.lower())}\b"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def get_all_keywords():
    return sorted(Keywords.keys())


# ---------------------------------------------------------
# Exclusion patterns
# ---------------------------------------------------------

EXCLUSION_PATTERNS = {
    "GSM": [
        r"\bgsm\s+(?:paper|papers)\b",
        r"\b\d+(?:\.\d+)?\s*gsm\b",
    ],

    "Fiber": [
        r"\bfiber\s+(?:reel|reels)\b",
        r"\bfiber\s+(?:paper|papers)\b",
        r"\bfiber\s+(?:cheque|cheques)\b",
        r"\bbiv\+fiber\b",
    ],

    "Storage": [
        r"\bcold\s+storage\b",
        r"\bbonded\s+storage\b",
        r"\bstorage\s+and\s+courier\b",
        r"\bstorage\s+services\b",
        r"\bstorage\s+facility\b",
        r"\bstorage\s+facilities\b",
    ],

    "Computer": [
        r"\bcomputer\s+numerical\s+control\b",
        r"\bcomputer\s+numerical\s+controlled\b",
        r"\bcomputer\s+grinding\s+machine\b",
        r"\bcnc\b",
    ],
}


def is_excluded(text, keyword):
    patterns = EXCLUSION_PATTERNS.get(keyword, [])

    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True

    return False


# ---------------------------------------------------------
# Capability mapping
# ---------------------------------------------------------

def get_capability_matches(matched_keywords):
    """
    Map matched keywords to the capabilities they belong to.

    Example:

    matched_keywords = ["Computer", "System"]

    returns:

    {
        "Computing & End-User Devices": 1,
        "Enterprise Software & ERP": 1
    }

    The value represents how many matched keywords belong
    to that capability.
    """

    capability_matches = {}

    matched_set = {
        keyword.lower()
        for keyword in matched_keywords
    }

    for capability_name, capability_data in CAPABILITIES.items():

        capability_keywords = {
            keyword.lower()
            for keyword in capability_data.get("keywords", [])
        }

        match_count = len(
            matched_set.intersection(capability_keywords)
        )

        if match_count > 0:
            capability_matches[capability_name] = match_count

    return capability_matches


# ---------------------------------------------------------
# Main keyword matching
# ---------------------------------------------------------

def find_keyword_matches(text):
    normalized_text = normalize_text(text)

    if not normalized_text:
        return {
            "matched_keywords": [],
            "keyword_count": 0,
            "keyword_score": 0.0,
            "capability_matches": {},
        }

    all_keywords = get_all_keywords()

    matched_keywords = []

    for keyword in all_keywords:

        # Check whether keyword exists as a complete word.
        if not keyword_exists(normalized_text, keyword):
            continue

        # Ignore known false-positive contexts.
        if is_excluded(normalized_text, keyword):
            continue

        matched_keywords.append(keyword)

    # No relevant keywords found.
    if not matched_keywords:
        return {
            "matched_keywords": [],
            "keyword_count": 0,
            "keyword_score": 0.0,
            "capability_matches": {},
        }

    # -----------------------------------------------------
    # Keyword scoring
    # -----------------------------------------------------
    #
    # Each unique matched keyword = 10 points.
    #
    # Examples:
    # 0 keywords = 0
    # 1 keyword  = 10
    # 2 keywords = 20
    # 3 keywords = 30
    #
    # The same keyword is counted only once because
    # matched_keywords contains unique keyword matches.
    # -----------------------------------------------------
    keyword_score = sum(
        Keywords[keyword]
        for keyword in matched_keywords
    )

    # -----------------------------------------------------
    # Capability mapping
    # -----------------------------------------------------

    capability_matches = get_capability_matches(
        matched_keywords
    )

    return {
        "matched_keywords": matched_keywords,
        "keyword_count": len(matched_keywords),
        "keyword_score": round(keyword_score, 4),
        "capability_matches": capability_matches,
    }