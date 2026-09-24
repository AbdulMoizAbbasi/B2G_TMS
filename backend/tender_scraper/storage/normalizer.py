import hashlib
import re


def _normalize_portal_name(portal):
    """
    Convert a portal name into a safe ID prefix.

    Example:
        'Federal PPRA' -> 'federal_ppra'
    """

    if not portal:
        return "unknown_portal"

    normalized = str(portal).strip().lower()

    normalized = re.sub(
        r"[^a-z0-9]+",
        "_",
        normalized,
    )

    normalized = normalized.strip("_")

    return normalized or "unknown_portal"


def _clean_value(value):
    """
    Convert a value into a clean string.
    """

    if value is None:
        return ""

    return str(value).strip()


def _get_stable_identifier(
    tender,
    portal,
):
    """
    Generate a stable identifier for a tender.

    Priority:

    1. Native tender number
    2. Sindh PPRA native tender number
    3. Balochistan TSENumber
    4. Detail URL
    5. Tender Notice URL
    6. Bidding Document URL
    7. Hash of stable tender fields

    The identifier is prefixed with the portal name
    to avoid collisions between portals.
    """

    portal_id = _normalize_portal_name(
        portal
    )

    # --------------------------------------------------------
    # 1. Standard tender number
    # --------------------------------------------------------

    tender_number = _clean_value(
        tender.get("tender_number")
    )

    # --------------------------------------------------------
    # 2. Sindh PPRA native tender number
    # --------------------------------------------------------

    if not tender_number:
        tender_number = _clean_value(
            tender.get("tenderNumber")
        )

    # --------------------------------------------------------
    # 3. Balochistan native identifier
    # --------------------------------------------------------

    if not tender_number:
        tender_number = _clean_value(
            tender.get("TSENumber")
        )

    if tender_number:

        safe_tender_number = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            tender_number
        )

        return (
            f"{portal_id}_"
            f"{safe_tender_number}"
        )

    # --------------------------------------------------------
    # 4. URLs that can uniquely identify the tender
    # --------------------------------------------------------

    possible_urls = [
        tender.get("detail_url"),
        tender.get("tender_notice_url"),
        tender.get("bidding_document_url"),
    ]

    for url in possible_urls:

        url = _clean_value(url)

        if url:

            url_hash = hashlib.sha256(
                url.encode("utf-8")
            ).hexdigest()[:16]

            return (
                f"{portal_id}_"
                f"{url_hash}"
            )

    # --------------------------------------------------------
    # 5. Generic stable-field fallback
    # --------------------------------------------------------

    #
    # Used only when no native ID or useful URL exists.
    #
    # Include portal-specific identifying fields where
    # available, while keeping the hash deterministic.
    #

    fallback_fields = [
        tender.get("Tender Title"),
        tender.get("tender_details"),
        tender.get("Name"),
        tender.get("name"),
        tender.get("procurement_title"),
        tender.get("procurement_type"),
        tender.get("Organization Name"),
        tender.get("organization_details"),
        tender.get("Agency"),
        tender.get("Department"),
        tender.get("departmentName"),
        tender.get("advertised_date"),
        tender.get("closing_date"),
        tender.get("Advertisement Date"),
        tender.get("Closing Date & Time"),
        tender.get("publishDate"),
    ]

    fallback_parts = [
        _clean_value(value)
        for value in fallback_fields
    ]

    fallback_text = "|".join(
        fallback_parts
    )

    fallback_hash = hashlib.sha256(
        fallback_text.encode("utf-8")
    ).hexdigest()[:16]

    return (
        f"{portal_id}_"
        f"{fallback_hash}"
    )


def normalize_tender(
    tender,
    portal,
    relevance,
    extra_fields=None,
):
    """
    Preserve the complete original scraped tender
    and add system-level fields.

    Final structure:

        <all original scraper fields>
        id
        source
        relevance

    No common-field transformation is performed.
    No 'other' field is created.

    extra_fields is retained for backward compatibility
    with existing pipeline calls but is intentionally ignored.
    """

    if not isinstance(
        tender,
        dict,
    ):
        raise ValueError(
            "tender must be a dictionary."
        )

    if not portal:
        raise ValueError(
            "portal cannot be empty."
        )

    if relevance is None:
        relevance = {}

    if not isinstance(
        relevance,
        dict,
    ):
        raise ValueError(
            "relevance must be a dictionary."
        )

    tender_id = _get_stable_identifier(
        tender,
        portal,
    )

    # --------------------------------------------------------
    # Preserve complete original scraper record
    # --------------------------------------------------------

    normalized = dict(tender)

    # --------------------------------------------------------
    # Add system-level fields
    # --------------------------------------------------------

    normalized["id"] = tender_id

    normalized["source"] = _clean_value(
        portal
    )

    normalized["relevance"] = dict(
        relevance
    )

    return normalized


if __name__ == "__main__":

    print("=" * 70)
    print("NORMALIZER TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # Federal-style tender
    # ---------------------------------------------------------

    federal_tender = {
        "web_tender_no": "TS0000012923E",

        "detail_url": (
            "https://epms.ppra.gov.pk/"
            "public/tenders/tender-details/"
            "TS0000012923E"
        ),

        "Tender Title": (
            "PROCUREMENT OF DESKTOP COMPUTERS"
        ),

        "Organization Name": (
            "Example Government Organization"
        ),

        "Office Name": (
            "Procurement Office"
        ),
    }

    federal_relevance = {
        "keyword_score": 20,
        "matched_keywords": [
            "Computer",
            "Desktop",
        ],
        "matched_capabilities": [
            "Computing & End-User Devices",
            "GPU & High-Performance Computing",
        ],
    }

    federal_result = normalize_tender(
        federal_tender,
        "Federal PPRA",
        federal_relevance,
    )

    print()
    print("Federal normalized tender:")
    print(federal_result)

    # ---------------------------------------------------------
    # Punjab-style tender
    # ---------------------------------------------------------

    punjab_tender = {
        "tender_number": "",

        "tender_details": (
            "Provision of Broadband Internet "
            "Connectivity Services"
        ),

        "organization_details": (
            "Example Government Organization"
        ),

        "status": "Active",

        "advertised_date": "09 Sep 2026",

        "closing_date": "26 Sep 2026",

        "detail_url": "",

        "tender_notice_url": (
            "https://eproc.punjab.gov.pk/"
            "Tenders/example.pdf"
        ),

        "bidding_document_url": (
            "https://eproc.punjab.gov.pk/"
            "BiddingDocuments/example.pdf"
        ),

        "procurement_title": (
            "Internet Connectivity Services"
        ),

        "procurement_type": "Services",
    }

    punjab_relevance = {
        "keyword_score": 20,
        "matched_keywords": [
            "Broadband",
            "Internet",
        ],
        "matched_capabilities": [
            "Broadband & Internet Connectivity",
            "Fiber & Network Infrastructure",
        ],
    }

    punjab_result = normalize_tender(
        punjab_tender,
        "Punjab PPRA",
        punjab_relevance,
    )

    print()
    print("Punjab normalized tender:")
    print(punjab_result)

    # ---------------------------------------------------------
    # Balochistan-style tender
    # ---------------------------------------------------------

    balochistan_tender = {
        "Id": 103601,

        "TSENumber": (
            "TSE-2627081169203"
        ),

        "Category": (
            "Power Supply Solar and Energy Works"
        ),

        "Agency": (
            "Balochistan Land Revenue "
            "Management Information System"
        ),

        "Department": (
            "Board of Revenue"
        ),

        "Name": (
            "Installation of Solar System "
            "at Hub & Turbat offices"
        ),

        "TenderStatus": "Close",

        "EstCost": "9800000",

        "District": "Quetta",

        "tenderNoticeDoc": "",

        "tenderBidDoc": (
            "f6800bfb-3caf-4c7f-ba45-"
            "c3947139d7c3.pdf"
        ),
    }

    balochistan_relevance = {
        "keyword_score": 0,
        "matched_keywords": [],
        "matched_capabilities": [],
    }

    balochistan_result = normalize_tender(
        balochistan_tender,
        "Balochistan PPRA",
        balochistan_relevance,
    )

    print()
    print("Balochistan normalized tender:")
    print(balochistan_result)

    # ---------------------------------------------------------
    # Sindh-style tender
    # ---------------------------------------------------------

    sindh_tender = {
        "publishedDocumentID": 704865,

        "tenderNumber": "S-26090824916",

        "tenderNumbers": "EPADS-S-26090824916",

        "name": "Firewall",

        "departmentName": "Sukkur IBA",

        "publishDate": "2026-09-15T19:45:52.63",

        "lastSubmissionDate": "2026-10-05T15:00:00",
    }

    sindh_relevance = {
        "keyword_score": 20,
        "matched_keywords": [
            "Firewall",
        ],
        "matched_capabilities": [
            "Cybersecurity & Network Security",
        ],
    }

    sindh_result = normalize_tender(
        sindh_tender,
        "Sindh PPRA",
        sindh_relevance,
    )

    print()
    print("Sindh normalized tender:")
    print(sindh_result)

    print()
    print("=" * 70)
    print("NORMALIZER TEST COMPLETE")
    print("=" * 70)