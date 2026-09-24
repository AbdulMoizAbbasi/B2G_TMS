from pathlib import Path
import os
import re

import pymupdf
import pytesseract
from PIL import Image


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

TESSERACT_PATH = os.getenv(
    "TESSERACT_CMD",
    DEFAULT_TESSERACT_PATH
)

pytesseract.pytesseract.tesseract_cmd = (
    TESSERACT_PATH
)


# =============================================================
# PDF OCR
# =============================================================

def extract_pdf_text(pdf_path):
    """
    Run OCR on every page of a scanned PDF.

    Returns:
        list of dictionaries:
        [
            {
                "page": 1,
                "text": "..."
            }
        ]
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    document = pymupdf.open(
        str(pdf_path)
    )

    pages = []

    try:

        for page_number, page in enumerate(
            document,
            start=1
        ):

            print(
                f"OCR processing page "
                f"{page_number}..."
            )

            # -------------------------------------------------
            # RENDER PAGE
            # -------------------------------------------------

            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(
                    2,
                    2
                ),
                alpha=False
            )

            image = Image.frombytes(
                "RGB",
                [
                    pixmap.width,
                    pixmap.height
                ],
                pixmap.samples
            )

            # -------------------------------------------------
            # TESSERACT
            # -------------------------------------------------

            text = pytesseract.image_to_string(
                image
            )

            pages.append(
                {
                    "page": page_number,
                    "text": text.strip()
                }
            )

    finally:

        document.close()

    return pages


# =============================================================
# TEXT HELPERS
# =============================================================

def normalize_text(text):
    """
    Normalize whitespace while preserving line
    boundaries where possible.
    """

    if not text:
        return None

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def clean_field(value):
    """
    Clean an extracted field without changing
    its actual meaning.
    """

    if value is None:
        return None

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value or None


def extract_field(text, pattern):
    """
    Extract a single field using a regex.
    """

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return None

    return clean_field(
        match.group(1)
    )


def extract_number(text, pattern):
    """
    Extract a numeric field.
    """

    value = extract_field(
        text,
        pattern
    )

    if value is None:
        return None

    match = re.search(
        r"\d+",
        value
    )

    if not match:
        return None

    try:
        return int(
            match.group(0)
        )

    except ValueError:
        return None


# =============================================================
# BID EVALUATION TABLE
# =============================================================

def extract_bid_evaluation_section(text):
    """
    Isolate the bid evaluation section.

    We only inspect the text between:

        11. Details of Bids Evaluation:

    and:

        12. Lowest Evaluated Bidder(s):

    This prevents unrelated numbers elsewhere in the
    document from being interpreted as bidder data.
    """

    match = re.search(
        r"11\.\s*Details of Bids Evaluation:"
        r"(.*?)"
        r"12\.\s*Lowest Evaluated Bidder",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    return match.group(1).strip()


def extract_bid_evaluations(text):
    """
    Extract bidder rows conservatively.

    IMPORTANT:
    If the OCR layout is not clear enough, this
    function returns an empty list instead of
    inventing incorrect bidder information.
    """

    section = extract_bid_evaluation_section(
        text
    )

    if not section:
        return []

    lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip()
    ]

    # ---------------------------------------------------------
    # Find candidate lines containing:
    #
    # bidder + Yes/No + numeric price
    #
    # Example:
    #
    # 1 BP Singapore Yes 26.969
    # ---------------------------------------------------------

    candidates = []

    for line in lines:

        match = re.match(
            r"^\d+\s+"
            r"(.+?)\s+"
            r"(Yes|No)\s+"
            r"(\d+(?:\.\d+)?)"
            r"(?:\s+(.*))?$",
            line,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        bidder = clean_field(
            match.group(1)
        )

        technical_status = (
            match.group(2)
        )

        contract_price = (
            match.group(3)
        )

        remaining = (
            match.group(4)
        )

        # -----------------------------------------------------
        # Basic safety checks
        # -----------------------------------------------------

        if not bidder:
            continue

        # Avoid obvious OCR/table header fragments.
        invalid_fragments = [
            "tender inquiry",
            "ppra ref",
            "rule",
            "regulation",
            "policy",
            "basis",
        ]

        bidder_lower = bidder.lower()

        if any(
            fragment in bidder_lower
            for fragment in invalid_fragments
        ):
            continue

        candidates.append(
            {
                "bidder": bidder,
                "technically_qualified":
                    technical_status,
                "contract_price":
                    contract_price,
                "delivery_period":
                    None,
            }
        )

    # ---------------------------------------------------------
    # DELIVERY PERIOD
    # ---------------------------------------------------------

    delivery_match = re.search(
        r"(\d{1,2}\s*[-–]\s*"
        r"\d{1,2}\s+"
        r"[A-Za-z]+\s+"
        r"\d{4})",
        section,
        flags=re.IGNORECASE
    )

    delivery_period = None

    if delivery_match:

        delivery_period = (
            delivery_match.group(1)
        )

    for candidate in candidates:

        candidate[
            "delivery_period"
        ] = delivery_period

    return candidates


# =============================================================
# LOWEST EVALUATED BIDDER
# =============================================================

def extract_lowest_evaluated_bidder(text):
    """
    Extract the lowest evaluated bidder section
    conservatively.

    The bidder name is extracted directly from the
    explicit 'Lowest Evaluated Bidder Name' field.

    Contract price is only extracted if it can be
    associated confidently with the section.
    """

    # ---------------------------------------------------------
    # Isolate section 12
    # ---------------------------------------------------------

    section_match = re.search(
        r"12\.\s*Lowest Evaluated Bidder"
        r"(.*?)"
        r"13\.\s*Any other",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not section_match:
        return None

    section = section_match.group(1)

    # ---------------------------------------------------------
    # Bidder name
    # ---------------------------------------------------------

    name = extract_field(
        section,
        r"Lowest Evaluated Bidder Name\s+(.+?)(?:\n|$)"
    )

    # ---------------------------------------------------------
    # Delivery period
    # ---------------------------------------------------------

    delivery_match = re.search(
        r"Delivery Periods?\s+"
        r"(\d{1,2}\s*[-–]\s*"
        r"\d{1,2}\s+"
        r"[A-Za-z]+\s+"
        r"\d{4})",
        section,
        flags=re.IGNORECASE
    )

    delivery_period = None

    if delivery_match:

        delivery_period = (
            delivery_match.group(1)
        )

    # ---------------------------------------------------------
    # Contract price
    #
    # Do NOT guess from arbitrary numbers.
    #
    # We will rely on bid_evaluations for the
    # actual contract price unless a clearly labelled
    # value is available.
    # ---------------------------------------------------------

    result = {
        "name": name,
        "contract_price": None,
        "delivery_period": delivery_period,
    }

    if all(
        value is None
        for value in result.values()
    ):

        return None

    return result


# =============================================================
# STRUCTURED OCR DATA
# =============================================================

def extract_ocr_data(pages):
    """
    Convert OCR pages into structured OCR data.

    IMPORTANT:
    This function ONLY produces OCR data.

    It must never overwrite or modify
    scraper-fetched information.
    """

    raw_text = "\n\n".join(
        page["text"]
        for page in pages
        if page.get("text")
    )

    raw_text = normalize_text(
        raw_text
    )

    if not raw_text:

        return {
            "raw_text": "",
            "procuring_agency": None,
            "procurement_method": None,
            "procurement_title": None,
            "tender_inquiry_no": None,
            "ppra_ref_no": None,
            "bid_closing": None,
            "bid_opening": None,
            "bids_received": None,
            "evaluation_criteria": None,
            "financial_bid_opening": None,
            "bid_evaluations": [],
            "lowest_evaluated_bidder": None,
            "additional_information": None,
        }

    # =========================================================
    # STANDARD FIELDS
    # =========================================================

    procuring_agency = extract_field(
        raw_text,
        r"Name of Procuring Agency:\s*(.+?)(?:\n|$)"
    )

    procurement_method = extract_field(
        raw_text,
        r"Method of Procurement:\s*(.+?)(?:\n|$)"
    )

    procurement_title = extract_field(
        raw_text,
        r"Title of Procurement:\s*(.+?)(?:\n|$)"
    )

    tender_inquiry_no = extract_field(
        raw_text,
        r"Tender Inquiry No\.?\s*(?:No\.)?:?\s*(.+?)(?:\n|$)"
    )

    ppra_ref_no = extract_field(
        raw_text,
        r"PPRA Ref\. No\.?\s*\(TSE\):\s*(.+?)(?:\n|$)"
    )

    bid_closing = extract_field(
        raw_text,
        r"Date & Time of Bid Closing:\s*(.+?)(?:\n|$)"
    )

    bid_opening = extract_field(
        raw_text,
        r"Date & Time of Bid Opening:\s*(.+?)(?:\n|$)"
    )

    bids_received = extract_number(
        raw_text,
        r"No of Bids Received:\s*(.+?)(?:\n|$)"
    )

    evaluation_criteria = extract_field(
        raw_text,
        r"Criteria for Bid Evaluation:\s*(.+?)(?:\n|$)"
    )

    financial_bid_opening = extract_field(
        raw_text,
        r"Date & Time of Financial Bid Opening:\s*(.+?)(?:\n|$)"
    )

    additional_information = extract_field(
        raw_text,
        r"additional\s*/\s*supporting information.*?:\s*(.+?)(?:\n|$)"
    )

    # =========================================================
    # BID EVALUATIONS
    # =========================================================

    bid_evaluations = extract_bid_evaluations(
        raw_text
    )

    # =========================================================
    # LOWEST EVALUATED BIDDER
    # =========================================================

    lowest_evaluated_bidder = (
        extract_lowest_evaluated_bidder(
            raw_text
        )
    )

    # =========================================================
    # FINAL DATA
    # =========================================================

    return {
        "raw_text": raw_text,

        "procuring_agency":
            procuring_agency,

        "procurement_method":
            procurement_method,

        "procurement_title":
            procurement_title,

        "tender_inquiry_no":
            tender_inquiry_no,

        "ppra_ref_no":
            ppra_ref_no,

        "bid_closing":
            bid_closing,

        "bid_opening":
            bid_opening,

        "bids_received":
            bids_received,

        "evaluation_criteria":
            evaluation_criteria,

        "financial_bid_opening":
            financial_bid_opening,

        "bid_evaluations":
            bid_evaluations,

        "lowest_evaluated_bidder":
            lowest_evaluated_bidder,

        "additional_information":
            additional_information,
    }


# =============================================================
# MAIN OCR FUNCTION
# =============================================================

def process_evaluation_pdf(pdf_path):
    """
    Run OCR and return structured OCR data.
    """

    pages = extract_pdf_text(
        pdf_path
    )

    return extract_ocr_data(
        pages
    )


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    pdf_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "evaluation_pdfs"
        / "TS0000012466E"
        / "EVL00000003147.pdf"
    )

    print("=" * 70)
    print(
        "FEDERAL PPRA EVALUATION OCR"
    )
    print("=" * 70)

    print(
        f"PDF: {pdf_path}"
    )

    print(
        f"Tesseract: {TESSERACT_PATH}"
    )

    ocr_data = process_evaluation_pdf(
        pdf_path
    )

    # =========================================================
    # PRINT STRUCTURED DATA
    # =========================================================

    print(
        "\n" + "=" * 70
    )
    print(
        "STRUCTURED OCR DATA"
    )
    print(
        "=" * 70
    )

    print(
        f"\nProcuring Agency:"
        f"\n{ocr_data['procuring_agency']}"
    )

    print(
        f"\nProcurement Method:"
        f"\n{ocr_data['procurement_method']}"
    )

    print(
        f"\nProcurement Title:"
        f"\n{ocr_data['procurement_title']}"
    )

    print(
        f"\nTender Inquiry No.:"
        f"\n{ocr_data['tender_inquiry_no']}"
    )

    print(
        f"\nPPRA Ref. No.:"
        f"\n{ocr_data['ppra_ref_no']}"
    )

    print(
        f"\nBid Closing:"
        f"\n{ocr_data['bid_closing']}"
    )

    print(
        f"\nBid Opening:"
        f"\n{ocr_data['bid_opening']}"
    )

    print(
        f"\nBids Received:"
        f"\n{ocr_data['bids_received']}"
    )

    print(
        f"\nEvaluation Criteria:"
        f"\n{ocr_data['evaluation_criteria']}"
    )

    print(
        f"\nFinancial Bid Opening:"
        f"\n{ocr_data['financial_bid_opening']}"
    )

    print(
        "\nBid Evaluations:"
    )

    if ocr_data["bid_evaluations"]:

        for index, bid in enumerate(
            ocr_data["bid_evaluations"],
            start=1
        ):

            print(
                f"\n  Bid #{index}"
            )

            print(
                f"  Bidder: "
                f"{bid['bidder']}"
            )

            print(
                f"  Technically Qualified: "
                f"{bid['technically_qualified']}"
            )

            print(
                f"  Contract Price: "
                f"{bid['contract_price']}"
            )

            print(
                f"  Delivery Period: "
                f"{bid['delivery_period']}"
            )

    else:

        print(
            "  No bidder rows confidently extracted."
        )

    print(
        "\nLowest Evaluated Bidder:"
    )

    print(
        ocr_data[
            "lowest_evaluated_bidder"
        ]
    )

    print(
        "\nAdditional Information:"
    )

    print(
        ocr_data[
            "additional_information"
        ]
    )

    print(
        "\n" + "=" * 70
    )
    print(
        "RAW OCR TEXT"
    )
    print(
        "=" * 70
    )

    print(
        ocr_data["raw_text"]
    )

    print(
        "\n" + "=" * 70
    )
    print(
        "END OCR TEST"
    )
    print(
        "=" * 70
    )