import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from tender_scraper.storage.checkpoint import get_checkpoint


BASE_URL = "http://www.kppra.gov.pk/kppra"
ACTIVE_TENDERS_URL = f"{BASE_URL}/activetenders.php"

PORTAL_NAME = "KP PPRA"

REQUEST_TIMEOUT = 60


# ============================================================
# SESSION
# ============================================================

def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })

    return session


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    else:
        value = str(value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_absolute_url(href):
    if not href:
        return ""

    href = href.strip()

    if href.startswith("http://"):
        return href

    if href.startswith("https://"):
        return href

    return urljoin(
        f"{BASE_URL}/",
        href,
    )


def parse_tender_date(value):
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

    for date_format in formats:
        try:
            return datetime.strptime(
                value,
                date_format,
            ).date()

        except ValueError:
            continue

    return None


# ============================================================
# FILTERED TENDER URL
# ============================================================

def build_tender_detail_url(tender_no):
    """
    Build the KPPRA active-tenders URL filtered
    specifically for the tender number.

    The Action column is NOT used.
    """

    tender_no = str(tender_no).strip()

    if not tender_no:
        return ""

    return (
        f"{ACTIVE_TENDERS_URL}"
        f"?tender_ref={tender_no}"
        f"&fromDate="
        f"&toDate="
        f"&dpart_id="
        f"&tender_type_id="
        f"&sort_field="
        f"&sort_order="
        f"&keywords="
        f"&search=Search"
    )


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(
    session,
    date_from,
    page=1,
):
    """
    Fetch one KPPRA active-tender page.

    date_from:
        Advertisement date in YYYY-MM-DD format.

    page:
        KPPRA pagination number.
    """

    params = {
        "fromDate": date_from,
        "toDate": "",
        "dpart_id": "",
        "tender_type_id": "",
        "sort_field": "",
        "sort_order": "",
        "keywords": "",
        "search": "Search",
    }

    if page > 1:
        params["p"] = page

    print()
    print("-" * 70)

    print(
        f"[KP PPRA] Fetching advertisement date: "
        f"{date_from}"
    )

    print(
        f"[KP PPRA] Page: {page}"
    )

    try:

        response = session.get(
            ACTIVE_TENDERS_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as exc:

        print(
            f"[KP PPRA] Request failed: {exc}"
        )

        return None

    print(
        f"[KP PPRA] HTTP Status: "
        f"{response.status_code}"
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


# ============================================================
# PAGINATION
# ============================================================

def get_total_pages(soup):
    """
    Detect KPPRA pagination links.

    Example:

        p=1
        p=2
        p=3
        ...
    """

    if soup is None:
        return 0

    pages = []

    for link in soup.find_all(
        "a",
        href=True,
    ):

        href = link.get(
            "href",
            "",
        )

        text = clean_text(link)

        if not text.isdigit():
            continue

        match = re.search(
            r"(?:[?&])p=(\d+)",
            href,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        try:
            page_number = int(
                match.group(1)
            )

        except ValueError:
            continue

        pages.append(
            page_number
        )

    if not pages:
        return 1

    return max(pages)


# ============================================================
# EXTRACT DOCUMENT URL
# ============================================================

def extract_document_from_cell(cell):
    """
    Extract a document URL from a tender/EOI or
    bidding-document cell.

    If no link exists, preserve the cell text.
    """

    if cell is None:
        return ""

    link = cell.find(
        "a",
        href=True,
    )

    if link:

        href = link.get(
            "href",
            "",
        ).strip()

        if href:
            return make_absolute_url(
                href
            )

    return clean_text(cell)


# ============================================================
# EXTRACT TENDERS
# ============================================================

def extract_tenders(soup):
    """
    Extract KP active tenders.

    Expected columns:

        0 Tender No
        1 Tender Description
        2 Procurement Entity
        3 Date of Advertisement
        4 Closing Date
        5 Tender/EOI
        6 Bidding Documents
        7 Action

    Action is intentionally ignored.
    """

    if soup is None:
        return []

    table = soup.find(
        "table"
    )

    if not table:
        print(
            "[KP PPRA] Tender table not found."
        )

        return []

    tbody = table.find(
        "tbody"
    )

    if tbody:
        rows = tbody.find_all(
            "tr"
        )
    else:
        rows = table.find_all(
            "tr"
        )

    tenders = []

    for row in rows:

        cells = row.find_all(
            "td"
        )

        if len(cells) < 7:
            continue

        tender_no = clean_text(
            cells[0]
        )

        if not tender_no:
            continue

        tender_description = clean_text(
            cells[1]
        )

        procurement_entity = clean_text(
            cells[2]
        )

        advertised_date = clean_text(
            cells[3]
        )

        closing_date = clean_text(
            cells[4]
        )

        tender_notice_url = (
            extract_document_from_cell(
                cells[5]
            )
        )

        bidding_document_url = (
            extract_document_from_cell(
                cells[6]
            )
        )

        detail_url = (
            build_tender_detail_url(
                tender_no
            )
        )

        tender = {
            "tender_number": tender_no,

            "tender_details": (
                tender_description
            ),

            "organization_details": (
                procurement_entity
            ),

            "advertised_date": (
                advertised_date
            ),

            "closing_date": (
                closing_date
            ),

            "tender_notice_url": (
                tender_notice_url
            ),

            "bidding_document_url": (
                bidding_document_url
            ),

            "detail_url": (
                detail_url
            ),
        }

        tenders.append(
            tender
        )

    return tenders


# ============================================================
# UNIQUE KEY
# ============================================================

def get_tender_unique_key(tender):
    """
    KP KPPRA exposes a native Tender No.

    Use it as the primary unique key.
    """

    tender_number = str(
        tender.get(
            "tender_number",
            "",
        )
    ).strip()

    if tender_number:
        return tender_number

    detail_url = str(
        tender.get(
            "detail_url",
            "",
        )
    ).strip()

    if detail_url:
        return detail_url

    return ""


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_tenders(tenders):

    unique_tenders = []

    seen = set()

    for tender in tenders:

        key = get_tender_unique_key(
            tender
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        unique_tenders.append(
            tender
        )

    return unique_tenders


# ============================================================
# CHECKPOINT FILTER
# ============================================================

def filter_checkpoint_tenders(
    tenders,
    checkpoint_date,
    checkpoint_key,
):
    """
    KP tenders are scraped one advertisement date
    at a time.

    On the checkpoint date:

        tenders appearing before the checkpoint
        are considered already processed.

    If the checkpoint tender cannot be found,
    return all tenders conservatively.
    """

    if not checkpoint_key:
        return tenders

    if not tenders:
        return []

    checkpoint_date_obj = (
        parse_tender_date(
            checkpoint_date
        )
    )

    if checkpoint_date_obj is None:
        print(
            "[KP PPRA] Could not parse checkpoint date."
        )

        return tenders

    checkpoint_index = None

    for index, tender in enumerate(
        tenders
    ):

        tender_date = parse_tender_date(
            tender.get(
                "advertised_date",
                "",
            )
        )

        if tender_date != checkpoint_date_obj:
            continue

        tender_key = (
            get_tender_unique_key(
                tender
            )
        )

        if (
            tender_key
            == str(
                checkpoint_key
            ).strip()
        ):

            checkpoint_index = index

            break

    if checkpoint_index is None:

        print(
            "[KP PPRA] Checkpoint tender "
            "was not found in the date result."
        )

        print(
            "[KP PPRA] Returning all tenders "
            "for this date conservatively."
        )

        return tenders

    return tenders[
        checkpoint_index + 1:
    ]


# ============================================================
# SCRAPE ONE DATE
# ============================================================

def scrape_date(
    session,
    current_date,
):
    """
    Scrape all KP tenders advertised on one date.

    Handles pagination.
    """

    date_string = current_date.strftime(
        "%Y-%m-%d"
    )

    first_soup = fetch_page(
        session=session,
        date_from=date_string,
        page=1,
    )

    if first_soup is None:
        return None

    first_page_tenders = (
        extract_tenders(
            first_soup
        )
    )

    total_pages = get_total_pages(
        first_soup
    )

    print(
        f"[KP PPRA] Date {date_string}: "
        f"Page 1 = "
        f"{len(first_page_tenders)} tenders"
    )

    print(
        f"[KP PPRA] Total pages: "
        f"{total_pages}"
    )

    all_date_tenders = []

    all_date_tenders.extend(
        first_page_tenders
    )

    for page in range(
        2,
        total_pages + 1,
    ):

        page_soup = fetch_page(
            session=session,
            date_from=date_string,
            page=page,
        )

        if page_soup is None:
            return None

        page_tenders = extract_tenders(
            page_soup
        )

        print(
            f"[KP PPRA] Date {date_string}: "
            f"Page {page} = "
            f"{len(page_tenders)} tenders"
        )

        all_date_tenders.extend(
            page_tenders
        )

    return deduplicate_tenders(
        all_date_tenders
    )


# ============================================================
# CHECKPOINT CANDIDATE
# ============================================================

def build_checkpoint_candidate(
    scraped_tenders,
    current_date,
):
    """
    Build checkpoint metadata from the latest
    tender reached during the current scrape.

    Because KP is scraped date-by-date, the last
    tender in the final successfully scraped date
    becomes the checkpoint candidate.
    """

    if not scraped_tenders:
        return None

    last_tender = scraped_tenders[-1]

    tender_key = (
        get_tender_unique_key(
            last_tender
        )
    )

    if not tender_key:
        return None

    return {
        "last_date": current_date.strftime(
            "%Y-%m-%d"
        ),
        "last_tender_key": tender_key,
    }


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_kp_tenders(
    start_date=None,
    end_date=None,
    use_checkpoint=True,
):
    """
    Scrape KP KPPRA active tenders incrementally.

    Date filtering is performed using:

        fromDate = advertisement date

    Each advertisement date is scraped separately.

    Pagination is then processed using:

        p=1
        p=2
        p=3
        ...

    This function does NOT update the checkpoint.
    """

    # --------------------------------------------------------
    # READ CHECKPOINT
    # --------------------------------------------------------

    checkpoint = get_checkpoint(
        PORTAL_NAME
    )

    checkpoint_date = checkpoint.get(
        "last_date"
    )

    checkpoint_key = checkpoint.get(
        "last_tender_key"
    )

    checkpoint_candidate = {
        "last_date": checkpoint_date,
        "last_tender_key": checkpoint_key,
    }

    print()
    print("=" * 70)
    print("KP PPRA - CHECKPOINT")
    print("=" * 70)

    print(
        f"Use checkpoint: "
        f"{use_checkpoint}"
    )

    print(
        f"Last date: "
        f"{checkpoint_date}"
    )

    print(
        f"Last tender key: "
        f"{checkpoint_key}"
    )

    # --------------------------------------------------------
    # PARSE START DATE
    # --------------------------------------------------------

    if start_date:

        configured_start_date = (
            parse_tender_date(
                start_date
            )
        )

        if configured_start_date is None:

            raise ValueError(
                "start_date must be YYYY-MM-DD"
            )

    else:

        configured_start_date = None

    # --------------------------------------------------------
    # DETERMINE EFFECTIVE START DATE
    # --------------------------------------------------------

    if (
        use_checkpoint
        and checkpoint_date
    ):

        checkpoint_date_obj = (
            parse_tender_date(
                checkpoint_date
            )
        )

        if checkpoint_date_obj is None:

            raise ValueError(
                "Invalid KP checkpoint date."
            )

        effective_start_date = (
            checkpoint_date_obj
        )

    else:

        if configured_start_date is None:

            raise ValueError(
                "start_date is required when "
                "no checkpoint exists."
            )

        effective_start_date = (
            configured_start_date
        )

    # --------------------------------------------------------
    # DETERMINE END DATE
    # --------------------------------------------------------

    if end_date:

        effective_end_date = (
            parse_tender_date(
                end_date
            )
        )

        if effective_end_date is None:

            raise ValueError(
                "end_date must be YYYY-MM-DD"
            )

    else:

        effective_end_date = (
            datetime.today().date()
        )

    if (
        effective_start_date
        > effective_end_date
    ):

        raise ValueError(
            "Start date cannot be after end date."
        )

    print()
    print("=" * 70)
    print("KP PPRA - SCRAPE RANGE")
    print("=" * 70)

    print(
        f"Effective start date: "
        f"{effective_start_date}"
    )

    print(
        f"End date: "
        f"{effective_end_date}"
    )

    # --------------------------------------------------------
    # CREATE SESSION
    # --------------------------------------------------------

    session = create_session()

    all_tenders = []

    current_date = effective_start_date

    # --------------------------------------------------------
    # SCRAPE DATE BY DATE
    # --------------------------------------------------------

    while current_date <= effective_end_date:

        date_string = current_date.strftime(
            "%Y-%m-%d"
        )

        print()
        print("=" * 70)

        print(
            f"KP PPRA - DATE: "
            f"{date_string}"
        )

        print("=" * 70)

        date_tenders = scrape_date(
            session=session,
            current_date=current_date,
        )

        if date_tenders is None:

            print(
                f"[KP PPRA] Failed to scrape "
                f"{date_string}."
            )

            return {
                "portal": PORTAL_NAME,
                "tenders": all_tenders,
                "checkpoint": checkpoint_candidate,
                "success": False,
            }

        # ----------------------------------------------------
        # CHECKPOINT FILTER
        # ----------------------------------------------------

        if (
            use_checkpoint
            and checkpoint_date
            and checkpoint_key
            and date_string == checkpoint_date
        ):

            date_tenders = (
                filter_checkpoint_tenders(
                    tenders=date_tenders,
                    checkpoint_date=checkpoint_date,
                    checkpoint_key=checkpoint_key,
                )
            )

        # ----------------------------------------------------
        # ADD RESULTS
        # ----------------------------------------------------

        all_tenders.extend(
            date_tenders
        )

        # ----------------------------------------------------
        # CHECKPOINT CANDIDATE
        # ----------------------------------------------------

        if date_tenders:

            checkpoint_candidate = (
                build_checkpoint_candidate(
                    scraped_tenders=date_tenders,
                    current_date=current_date,
                )
            )

        print(
            f"[KP PPRA] Tenders returned "
            f"for {date_string}: "
            f"{len(date_tenders)}"
        )

        current_date += timedelta(
            days=1
        )

    # --------------------------------------------------------
    # FINAL DEDUPLICATION
    # --------------------------------------------------------

    before_dedup = len(
        all_tenders
    )

    all_tenders = deduplicate_tenders(
        all_tenders
    )

    duplicates_removed = (
        before_dedup
        - len(all_tenders)
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("KP PPRA - FINAL RESULT")
    print("=" * 70)

    print(
        f"Date range: "
        f"{effective_start_date} "
        f"to "
        f"{effective_end_date}"
    )

    print(
        f"Tenders before deduplication: "
        f"{before_dedup}"
    )

    print(
        f"Duplicates removed: "
        f"{duplicates_removed}"
    )

    print(
        f"Tenders returned: "
        f"{len(all_tenders)}"
    )

    print(
        f"Checkpoint candidate: "
        f"{checkpoint_candidate}"
    )

    return {
        "portal": PORTAL_NAME,
        "tenders": all_tenders,
        "checkpoint": checkpoint_candidate,
        "success": True,
    }


# ============================================================
# DIRECT TEST
# ============================================================
if __name__ == "__main__":

    result = scrape_kp_tenders(
        start_date="2026-09-24",
        end_date="2026-09-24",
        use_checkpoint=False,
    )

    print()
    print("=" * 70)
    print("KP TENDER SAMPLE")
    print("=" * 70)

    if result["tenders"]:
        print(result["tenders"][0])