
import re

from tender_scraper.config.keywords import Keywords
from tender_scraper.config.capabilities import CAPABILITIES
from tender_scraper.config.remove_keywords import REMOVE_KEYWORDS


def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def keyword_exists(text, keyword):
    pattern = rf"\b{re.escape(keyword)}\b"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def get_all_keywords():
    return sorted(Keywords.keys())


def get_suppressed_spans(text, keyword):
    """
    Return negative-rule spans that apply to this keyword.

    A positive keyword occurrence is suppressed only when its
    span overlaps an enabled exclusion pattern.
    """
    rule = REMOVE_KEYWORDS.get(keyword, {})

    if not rule.get("enabled", False):
        return []

    spans = []

    for pattern in rule.get("patterns", []):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append({
                "start": match.start(),
                "end": match.end(),
                "phrase": match.group(0),
                "reason": rule.get(
                    "reason",
                    "Configured negative-keyword rule",
                ),
            })

    return spans


def get_keyword_occurrences(text, keyword):
    """Return every whole-word occurrence of a keyword."""
    pattern = rf"\b{re.escape(keyword)}\b"

    return list(
        re.finditer(pattern, text, flags=re.IGNORECASE)
    )


def get_capability_matches(matched_keywords):
    """
    Map retained keywords to their capabilities.
    Each unique keyword is counted once per capability.
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


def find_keyword_matches(text):
    normalized_text = normalize_text(text)

    if not normalized_text:
        return {
            "matched_keywords": [],
            "keyword_count": 0,
            "keyword_score": 0.0,
            "capability_matches": {},
            "suppressed_matches": [],
        }

    matched_keywords = []
    suppressed_matches = []

    for keyword in get_all_keywords():
        occurrences = get_keyword_occurrences(
            normalized_text,
            keyword,
        )

        if not occurrences:
            continue

        exclusion_spans = get_suppressed_spans(
            normalized_text,
            keyword,
        )

        has_retained_occurrence = False

        for occurrence in occurrences:
            overlapping_rule = next(
                (
                    rule
                    for rule in exclusion_spans
                    if occurrence.start() < rule["end"]
                    and occurrence.end() > rule["start"]
                ),
                None,
            )

            if overlapping_rule:
                suppressed_matches.append({
                    "keyword": keyword,
                    "matched_text": occurrence.group(0),
                    "context": overlapping_rule["phrase"],
                    "reason": overlapping_rule["reason"],
                })
            else:
                has_retained_occurrence = True

        # Count a keyword if at least one occurrence survives.
        if has_retained_occurrence:
            matched_keywords.append(keyword)

    keyword_score = sum(
        Keywords[keyword]
        for keyword in matched_keywords
    )

    capability_matches = get_capability_matches(
        matched_keywords
    )

    return {
        "matched_keywords": matched_keywords,
        "keyword_count": len(matched_keywords),
        "keyword_score": round(keyword_score, 4),
        "capability_matches": capability_matches,
        "suppressed_matches": suppressed_matches,
    }
