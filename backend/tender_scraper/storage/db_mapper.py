from datetime import datetime
from decimal import Decimal
import re


def clean_url(value):
    """
    Convert a URL or Markdown-style link into a plain URL.

    Examples:
        https://example.com
        [https://example.com](https://example.com)
    """
    if not value:
        return None

    value = str(value).strip()

    # Handle Markdown link format:
    # [https://example.com](https://example.com)
    match = re.fullmatch(r"\[.*?\]\((.*?)\)", value)

    if match:
        return match.group(1).strip()

    return value


def parse_federal_date(value):
    """
    Convert Federal PPRA date strings into Python datetime objects.
    """
    if not value:
        return None

    value = value.strip()

    formats = [
        "%B %d, %Y",
        "%B %d, %Y at %I:%M %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def parse_federal_estimated_value(bid_security):
    """
    Federal PPRA provides Bid Security.

    Estimated Value = Bid Security / 0.02
    """
    if bid_security is None:
        return None, None

    try:
        value = Decimal(str(bid_security).replace(",", "").strip())

        estimated_value = value / Decimal("0.02")

        return estimated_value, "calculated_from_bid_security"

    except (ValueError, TypeError, ArithmeticError):
        return None, None


def get_federal_primary_document_url(tender):
    """
    Return the URL of the Federal PPRA Tender Document.

    Advertisement is deliberately ignored.
    """
    documents = tender.get("Documents") or []

    for document in documents:
        if document.get("name") == "Download Tender Document":
            return clean_url(document.get("url"))

    return None


def get_federal_documents(tender):
    """
    Return only the Federal PPRA Tender Document.

    The Advertisement is intentionally excluded.
    """

    documents = tender.get("Documents") or []

    for document in documents:
        if document.get("name") == "Download Tender Document":
            url = clean_url(document.get("url"))

            if not url:
                return []

            return [
                {
                    "document_type": "PRIMARY",
                    "document_name": "Download Tender Document",
                    "source_url": url,
                }
            ]

    return []



def map_federal_tender(tender, relevance_result):
    """
    Map one Federal PPRA tender into the normalized DB structure.

    This function does not write to the database.
    """

    estimated_value, estimated_value_source = (
        parse_federal_estimated_value(
            tender.get("Bid Security")
        )
    )

    return {
        "source_id": 1,

        "web_tender_no": tender.get("web_tender_no"),

        "tender_reference_no": tender.get(
            "Tender No / Reference No / Tender Inquiry No"
        ),

        "tender_name": tender.get("Tender Title"),

        "city": tender.get("City"),

        "authority": tender.get("Organization Name"),

        "organization": tender.get("Office Name"),

        "estimated_value": estimated_value,

        "estimated_value_source": estimated_value_source,

        "advertised_date": parse_federal_date(
            tender.get("Advertisement Date")
        ),

        "closed_date": parse_federal_date(
            tender.get("Closing Date & Time")
        ),

        "source_detail_url": clean_url(
            tender.get("detail_url")
        ),

        "primary_document_url": get_federal_primary_document_url(
            tender
        ),

        "documents": get_federal_documents(tender),

        "raw_data": tender,

        "relevance": relevance_result.get("relevance", {}),
    }


def parse_punjab_date(value):
    """
    Convert Punjab PPRA date strings into Python datetime objects.
    """
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%d %b %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def get_punjab_primary_document_url(tender):
    """
    Return the Punjab PPRA Bidding Document URL.
    """
    return clean_url(
        tender.get("bidding_document_url")
    )


def get_punjab_documents(tender):
    """
    Return only the Punjab PPRA Bidding Document.
    """
    url = get_punjab_primary_document_url(tender)

    if not url:
        return []

    return [
        {
            "document_type": "PRIMARY",
            "document_name": "Bidding Document",
            "source_url": url,
        }
    ]


def map_punjab_tender(tender, relevance_result):
    """
    Map one Punjab PPRA tender into the normalized DB structure.

    This function does not write to the database.
    """
    return {
        "source_id": 3,

        "web_tender_no": None,

        "tender_reference_no": None,

        "tender_name": tender.get(
            "tender_details"
        ),

        "city": None,

        "authority": tender.get(
            "organization_details"
        ),

        "organization": tender.get(
            "organization_details"
        ),

        "estimated_value": None,

        "estimated_value_source": None,

        "advertised_date": parse_punjab_date(
            tender.get("advertised_date")
        ),

        "closed_date": parse_punjab_date(
            tender.get("closing_date")
        ),

        "source_detail_url": None,

        "primary_document_url": (
            get_punjab_primary_document_url(
                tender
            )
        ),

        "documents": get_punjab_documents(
            tender
        ),

        "raw_data": tender,

        "relevance": relevance_result.get(
            "relevance",
            {}
        ),
    }


def parse_kp_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def get_kp_primary_document_url(tender):
    value = clean_url(
        tender.get("bidding_document_url")
    )

    if not value:
        return None

    if not value.lower().startswith(
        ("http://", "https://")
    ):
        return None

    return value


def get_kp_documents(tender):
    url = get_kp_primary_document_url(tender)

    if not url:
        return []

    return [{
        "document_type": "PRIMARY",
        "document_name": "Bidding Document",
        "source_url": url,
    }]


def map_kp_tender(tender, relevance_result):
    return {
        "source_id": 2,
        "web_tender_no": tender.get("tender_number"),
        "tender_reference_no": None,
        "tender_name": tender.get("tender_details"),
        "city": None,
        "authority": None,
        "organization": tender.get("organization_details"),
        "estimated_value": None,
        "estimated_value_source": None,
        "advertised_date": parse_kp_date(
            tender.get("advertised_date")
        ),
        "closed_date": parse_kp_date(
            tender.get("closing_date")
        ),
        "source_detail_url": tender.get("detail_url"),
        "primary_document_url": get_kp_primary_document_url(
            tender
        ),
        "documents": get_kp_documents(tender),
        "raw_data": tender,
        "relevance": relevance_result.get(
            "relevance",
            {},
        ),
    }


def parse_balochistan_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def parse_balochistan_estimated_value(value):
    if value in (None, ""):
        return None

    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def get_balochistan_primary_document_url(tender):
    tender_id = tender.get("Id")

    if not tender_id:
        return None

    return (
        "https://bpptwo.vdc.services:9446/"
        f"Reports/GoodsProcurement/BiddingDocument.html?id={tender_id}"
    )


def get_balochistan_documents(tender):
    url = get_balochistan_primary_document_url(tender)

    if not url:
        return []

    return [{
        "document_type": "PRIMARY",
        "document_name": "Bidding Document",
        "source_url": url,
    }]


def map_balochistan_tender(tender, relevance_result):
    return {
        "source_id": 5,
        "web_tender_no": tender.get("TSENumber"),
        "tender_reference_no": None,
        "tender_name": tender.get("TenderName"),
        "city": tender.get("District"),
        "authority": tender.get("Department"),
        "organization": tender.get("Agency"),
        "estimated_value": parse_balochistan_estimated_value(
            tender.get("EstCost")
        ),
        "estimated_value_source": "source",
        "advertised_date": parse_balochistan_date(
            tender.get("PublishedDate")
        ),
        "closed_date": parse_balochistan_date(
            tender.get("CloseDate")
        ),
        "source_detail_url": None,
        "primary_document_url": get_balochistan_primary_document_url(tender),
        "documents": get_balochistan_documents(tender),
        "raw_data": tender,
        "relevance": relevance_result.get("relevance", {}),
    }



def parse_sindh_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def parse_sindh_estimated_value(value):
    if value in (None, ""):
        return None

    try:
        return float(
            str(value).replace(",", "").strip()
        )
    except (ValueError, TypeError):
        return None


def map_sindh_tender(tender, relevance_result):
    return {
        "source_id": 4,
        "web_tender_no": tender.get("tenderNumbers"),
        "tender_reference_no": tender.get("tenderNumber"),
        "tender_name": tender.get("name"),
        "city": tender.get("location"),
        "authority": tender.get("departmentName"),
        "organization": tender.get("departmentName"),
        "estimated_value": parse_sindh_estimated_value(
            tender.get("estimatedCost")
        ),
        "estimated_value_source": "source",
        "advertised_date": parse_sindh_date(
            tender.get("publishDate")
        ),
        "closed_date": parse_sindh_date(
            tender.get("lastSubmissionDate")
        ),
        "source_detail_url": None,
        "primary_document_url": None,
        "documents": [],
        "raw_data": tender,
        "relevance": relevance_result.get(
            "relevance",
            {},
        ),
    }