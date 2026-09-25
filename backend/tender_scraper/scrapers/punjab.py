import hashlib
import ssl
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from tender_scraper.storage.checkpoint import get_checkpoint


BASE_URL = "https://eproc.punjab.gov.pk"
ACTIVE_TENDERS_URL = f"{BASE_URL}/ActiveTenders.aspx"

PAGE_SIZE = 100

PORTAL_NAME = "Punjab PPRA"


class LegacyTLSAdapter(HTTPAdapter):
    """
    Punjab PPRA uses a legacy TLS configuration.
    This adapter allows requests to connect to the portal.
    """

    def init_poolmanager(
        self,
        connections,
        maxsize,
        block=False,
        **pool_kwargs,
    ):
        ctx = ssl.SSLContext(
            ssl.PROTOCOL_TLS_CLIENT
        )

        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2

        ctx.set_ciphers(
            "ECDHE-RSA-AES256-SHA"
        )

        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        pool_kwargs["ssl_context"] = ctx

        return super().init_poolmanager(
            connections,
            maxsize,
            block=block,
            **pool_kwargs,
        )


def create_session():
    """
    Create a requests session configured for Punjab PPRA.
    """

    session = requests.Session()

    session.mount(
        "https://",
        LegacyTLSAdapter(),
    )

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    return session


def fetch_active_tenders_page(session):
    """
    Fetch the initial Punjab PPRA Active Tenders page.

    The page provides the ASP.NET form state required
    for server-side filtering.
    """

    print()
    print("=" * 70)
    print("PUNJAB PPRA - ACTIVE TENDERS")
    print("=" * 70)

    print(
        f"URL: {ACTIVE_TENDERS_URL}"
    )

    try:
        response = session.get(
            ACTIVE_TENDERS_URL,
            timeout=60,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:

        print(
            f"Failed to access Punjab PPRA: {e}"
        )

        return None

    print(
        f"HTTP Status: {response.status_code}"
    )

    print(
        f"Page Size: {len(response.content):,} bytes"
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def build_form_data(soup):
    """
    Extract ASP.NET form fields from the current page.

    Dynamically captures:
    - __VIEWSTATE
    - __EVENTVALIDATION
    - __VIEWSTATEGENERATOR
    - Telerik state fields
    - Grid fields
    """

    if soup is None:
        return None

    form = soup.find("form")

    if not form:

        print(
            "ASP.NET form not found."
        )

        return None

    data = {}

    for inp in form.find_all("input"):

        name = inp.get("name")

        if not name:
            continue

        input_type = inp.get(
            "type",
            "text",
        ).lower()

        if input_type in {
            "submit",
            "button",
            "image",
            "file",
        }:
            continue

        data[name] = inp.get(
            "value",
            "",
        )

    return data


def fetch_tenders_by_publish_date(
    session,
    soup,
    date_string,
):
    """
    Apply Punjab PPRA's server-side Publish Date filter.

    Example:
        09 Sep 2026

    The request reproduces the Telerik RadGrid command:

        Filter;Publish_Date|09 Sep 2026|Contains
    """

    data = build_form_data(
        soup
    )

    if data is None:
        return None

    filter_input = (
        "ctl00$ContentPlaceHolderSRIS"
        "$rdgrdManageTender"
        "$ctl00$ctl02$ctl02"
        "$FilterTextBox_Publish_Date"
    )

    data[filter_input] = date_string

    data["__EVENTTARGET"] = (
        "ctl00$ContentPlaceHolderSRIS"
        "$rdgrdManageTender"
    )

    data["__EVENTARGUMENT"] = (
        "FireCommand:"
        "ctl00$ContentPlaceHolderSRIS"
        "$rdgrdManageTender"
        "$ctl00;Filter;"
        f"Publish_Date|{date_string}|Contains"
    )

    page_size_input = (
        "ctl00$ContentPlaceHolderSRIS"
        "$rdgrdManageTender"
        "$ctl00$ctl03$ctl01"
        "$PageSizeComboBox"
    )

    data[page_size_input] = str(
        PAGE_SIZE
    )

    print()
    print("=" * 70)

    print(
        "FILTERING PUNJAB PPRA BY PUBLISH DATE: "
        f"{date_string}"
    )

    print("=" * 70)

    try:
        response = session.post(
            ACTIVE_TENDERS_URL,
            data=data,
            headers={
                "Referer": ACTIVE_TENDERS_URL,
            },
            timeout=60,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:

        print(
            f"Failed to apply date filter: {e}"
        )

        return None

    print(
        f"HTTP Status: {response.status_code}"
    )

    print(
        f"Page Size: {len(response.content):,} bytes"
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def get_filtered_page_events(soup):
    """
    Extract Telerik pagination event targets.

    Returns:

        {
            1: "...",
            2: "...",
            3: "..."
        }
    """

    events = {}

    if soup is None:
        return events

    grid = soup.select_one(
        "#ctl00_ContentPlaceHolderSRIS_rdgrdManageTender"
    )

    if not grid:
        return events

    links = grid.find_all("a")

    for link in links:

        text = link.get_text(
            " ",
            strip=True,
        )

        href = link.get(
            "href",
            "",
        )

        if not text.isdigit():
            continue

        if "__doPostBack" not in href:
            continue

        try:

            inside = href.split(
                "__doPostBack('",
                1,
            )[1]

            event_target = inside.split(
                "'",
                1,
            )[0]

        except (IndexError, ValueError):

            continue

        page_number = int(text)

        events[page_number] = event_target

    return events


def fetch_filtered_page(
    session,
    filtered_soup,
    page,
):
    """
    Request another page from an already filtered
    Telerik grid.
    """

    if filtered_soup is None:
        return None

    events = get_filtered_page_events(
        filtered_soup
    )

    event_target = events.get(
        page
    )

    if not event_target:

        print(
            f"No pagination event found "
            f"for filtered page {page}."
        )

        return None

    data = build_form_data(
        filtered_soup
    )

    if data is None:
        return None

    data["__EVENTTARGET"] = event_target
    data["__EVENTARGUMENT"] = ""

    print()
    print("=" * 70)

    print(
        f"REQUESTING FILTERED PAGE {page}"
    )

    print("=" * 70)

    try:

        response = session.post(
            ACTIVE_TENDERS_URL,
            data=data,
            headers={
                "Referer": ACTIVE_TENDERS_URL,
            },
            timeout=60,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:

        print(
            f"Failed to fetch filtered page "
            f"{page}: {e}"
        )

        return None

    print(
        f"HTTP Status: {response.status_code}"
    )

    print(
        f"Page Size: {len(response.content):,} bytes"
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def make_absolute_url(href):
    """
    Convert a Punjab PPRA relative URL
    into an absolute URL.
    """

    if not href:
        return ""

    href = href.strip()

    if href.startswith("http://"):
        return href

    if href.startswith("https://"):
        return href

    return (
        BASE_URL
        + "/"
        + href.lstrip("/")
    )


def extract_tenders(soup):
    """
    Extract tender records from the Punjab PPRA
    Telerik grid.
    """

    if soup is None:
        return []

    table = soup.select_one(
        "#ctl00_ContentPlaceHolderSRIS_rdgrdManageTender"
    )

    if not table:

        print(
            "Tender grid not found."
        )

        return []

    rows = table.find_all("tr")

    tenders = []

    for row in rows:

        cells = row.find_all("td")

        # Expected columns:
        #
        # 0 Procurement Title
        # 1 Procurement Name
        # 2 Type
        # 3 Publish Date
        # 4 Close Date
        # 5 Department
        # 6 Status
        # 7 Tender Notice
        # 8 Bidding Document

        if len(cells) < 9:
            continue

        values = [
            cell.get_text(
                " ",
                strip=True,
            )
            for cell in cells
        ]

        if not any(values):
            continue

        tender_notice_url = ""
        bidding_document_url = ""

        links = row.find_all("a")

        for link in links:

            href = link.get("href")

            if not href:
                continue

            absolute_url = make_absolute_url(
                href
            )

            if "Tenders/" in href:

                tender_notice_url = (
                    absolute_url
                )

            elif "BiddingDocuments/" in href:

                bidding_document_url = (
                    absolute_url
                )

        tender = {
            # Punjab PPRA does not expose
            # a tender number in this grid.
            "tender_number": "",

            "tender_details": values[1],

            "organization_details": values[5],

            "status": values[6],

            "advertised_date": values[3],

            "closing_date": values[4],

            # Punjab currently has no separate
            # detail page URL in this grid.
            "detail_url": "",

            "tender_notice_url": (
                tender_notice_url
            ),

            "bidding_document_url": (
                bidding_document_url
            ),

            "procurement_title": values[0],

            "procurement_type": values[2],
        }

        tenders.append(
            tender
        )

    return tenders


def get_tender_unique_key(tender):
    """
    Generate a stable key for a Punjab tender.

    Priority:

    1. Tender Notice URL
    2. Bidding Document URL
    3. SHA-256 hash of identifying fields
    """

    tender_notice_url = (
        tender.get(
            "tender_notice_url",
            "",
        )
        or ""
    ).strip()

    if tender_notice_url:
        return tender_notice_url

    bidding_document_url = (
        tender.get(
            "bidding_document_url",
            "",
        )
        or ""
    ).strip()

    if bidding_document_url:
        return bidding_document_url

    raw = "|".join(
        [
            str(
                tender.get(
                    "procurement_title",
                    "",
                )
            ).strip(),

            str(
                tender.get(
                    "tender_details",
                    "",
                )
            ).strip(),

            str(
                tender.get(
                    "organization_details",
                    "",
                )
            ).strip(),

            str(
                tender.get(
                    "advertised_date",
                    "",
                )
            ).strip(),

            str(
                tender.get(
                    "closing_date",
                    "",
                )
            ).strip(),
        ]
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def deduplicate_tenders(tenders):
    """
    Remove duplicate tender records while
    preserving their original order.
    """

    unique_tenders = []
    seen = set()

    for tender in tenders:

        key = get_tender_unique_key(
            tender
        )

        if key in seen:
            continue

        seen.add(key)

        unique_tenders.append(
            tender
        )

    return unique_tenders


def parse_tender_date(date_string):
    """
    Parse tender dates from Punjab PPRA.

    Supports:

        09 Sep 2026
        2026-09-09
        09-09-2026
        09/09/2026
    """

    if not date_string:
        return None

    date_string = str(
        date_string
    ).strip()

    supported_formats = [
        "%d %b %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for date_format in supported_formats:

        try:

            return datetime.strptime(
                date_string,
                date_format,
            ).date()

        except ValueError:

            continue

    return None


def filter_checkpoint_tenders(
    tenders,
    checkpoint_date,
    checkpoint_key,
):
    """
    Remove tenders already processed according
    to the checkpoint.

    Punjab cannot filter by time, so the complete
    checkpoint date is downloaded again.

    The checkpoint tender is located in the
    portal's current ordering and only rows
    appearing after it are returned.

    If the checkpoint tender cannot be found,
    all tenders for that date are returned
    conservatively.
    """

    if not checkpoint_key:
        return tenders

    if not tenders:
        return []

    checkpoint_date_obj = parse_tender_date(
        checkpoint_date
    )

    if checkpoint_date_obj is None:

        print()
        print(
            "WARNING: Invalid checkpoint date."
        )

        print(
            f"Received: {checkpoint_date}"
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

        tender_key = get_tender_unique_key(
            tender
        )

        if tender_key == checkpoint_key:

            checkpoint_index = index

            break

    if checkpoint_index is None:

        print()
        print(
            "WARNING: Checkpoint tender was "
            "not found in the filtered result."
        )

        print(
            "Checkpoint tender may have been "
            "removed, reordered, or changed."
        )

        print(
            "No checkpoint-based rows will "
            "be discarded for this date."
        )

        return tenders

    new_tenders = tenders[
        checkpoint_index + 1:
    ]

    print()
    print("=" * 70)
    print("CHECKPOINT FILTER RESULT")
    print("=" * 70)

    print(
        f"Checkpoint position: "
        f"{checkpoint_index + 1}"
    )

    print(
        f"Tenders before checkpoint: "
        f"{checkpoint_index + 1}"
    )

    print(
        f"Tenders after checkpoint: "
        f"{len(new_tenders)}"
    )

    return new_tenders


def scrape_date(
    session,
    initial_soup,
    current_date,
):
    """
    Scrape all tenders published on one date.

    Handles server-side filtering and pagination.
    """

    date_string = current_date.strftime(
        "%d %b %Y"
    )

    filtered_soup = (
        fetch_tenders_by_publish_date(
            session,
            initial_soup,
            date_string,
        )
    )

    if filtered_soup is None:
        return None

    page_tenders = extract_tenders(
        filtered_soup
    )

    print()
    print("=" * 70)

    print(
        f"DATE: {date_string}"
    )

    print("=" * 70)

    print(
        f"Page 1 tenders: "
        f"{len(page_tenders)}"
    )

    all_date_tenders = []

    all_date_tenders.extend(
        page_tenders
    )

    # ------------------------------------------------------
    # Pagination
    # ------------------------------------------------------

    filtered_page_events = (
        get_filtered_page_events(
            filtered_soup
        )
    )

    if filtered_page_events:

        max_page = max(
            filtered_page_events.keys()
        )

        print(
            f"Filtered pages detected: "
            f"{max_page}"
        )

        current_filtered_soup = (
            filtered_soup
        )

        for page in range(
            2,
            max_page + 1,
        ):

            next_soup = (
                fetch_filtered_page(
                    session,
                    current_filtered_soup,
                    page,
                )
            )

            if next_soup is None:
                return None

            next_tenders = extract_tenders(
                next_soup
            )

            print(
                f"Filtered page {page}: "
                f"{len(next_tenders)} tenders"
            )

            all_date_tenders.extend(
                next_tenders
            )

            current_filtered_soup = (
                next_soup
            )

    return all_date_tenders


def scrape_punjab_tenders(
    start_date=None,
    end_date=None,
    use_checkpoint=True,
):
    """
    Scrape Punjab PPRA tenders incrementally.

    Checkpoint behavior:

    No checkpoint:
        Uses start_date/end_date.

    Existing checkpoint:
        ALWAYS starts from the checkpoint date.

        The configured start_date is ignored once a
        checkpoint exists.

        The complete checkpoint date is fetched because
        Punjab only supports date filtering.

        Previously processed rows are removed using
        last_tender_key when the checkpoint tender can
        be located.

        All dates after the checkpoint date are treated
        as new.

    Example:

        Configured start date:
            2026-09-01

        Checkpoint:
            2026-09-03

        Effective start:
            2026-09-03

        Therefore:
            2026-09-01  -> NOT scraped
            2026-09-02  -> NOT scraped
            2026-09-03  -> scraped + checkpoint filtered
            2026-09-04  -> scraped
            2026-09-05  -> scraped
            ...
            2026-09-09  -> scraped

    IMPORTANT:

        This function does NOT update the checkpoint.

        The main pipeline must update the checkpoint
        only after successful downstream processing
        and storage.
    """

    # ------------------------------------------------------
    # Read checkpoint
    # ------------------------------------------------------

    checkpoint = get_checkpoint(PORTAL_NAME)
    checkpoint_date = checkpoint.get("last_date")
    checkpoint_key = checkpoint.get("last_tender_key")
    checkpoint_candidate = {
    "last_date": checkpoint_date,
    "last_tender_key": checkpoint_key,
    }

    print()
    print("=" * 70)
    print("PUNJAB PPRA - CHECKPOINT")
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

    # ------------------------------------------------------
    # Parse configured start date
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # Determine effective start date
    # ------------------------------------------------------

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
                "Invalid checkpoint date. "
                "Expected YYYY-MM-DD."
            )

        # IMPORTANT:
        #
        # Once a checkpoint exists, the checkpoint
        # date becomes the scraping start date.
        #
        # Do NOT use max(configured_start_date,
        # checkpoint_date_obj).
        #
        # The configured date is only the initial
        # fallback when no checkpoint exists.

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

    # ------------------------------------------------------
    # Determine end date
    # ------------------------------------------------------

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
    print("PUNJAB PPRA - SCRAPE RANGE")
    print("=" * 70)

    if configured_start_date:

        print(
            f"Requested start date: "
            f"{configured_start_date}"
        )

    print(
        f"Effective start date: "
        f"{effective_start_date}"
    )

    print(
        f"End date: "
        f"{effective_end_date}"
    )

    # ------------------------------------------------------
    # Create session
    # ------------------------------------------------------

    session = create_session()

    # ------------------------------------------------------
    # Fetch initial page
    # ------------------------------------------------------

    initial_soup = fetch_active_tenders_page(
        session
    )

    if initial_soup is None:

        return {
            "portal": PORTAL_NAME,
            "tenders": [],
            "checkpoint": checkpoint,
            "success": False,
        }

    # ------------------------------------------------------
    # Scrape dates
    # ------------------------------------------------------

    all_tenders = []

    current_date = effective_start_date

    while current_date <= effective_end_date:

        date_tenders = scrape_date(
            session=session,
            initial_soup=initial_soup,
            current_date=current_date,
        )

        # ---------------------------------------------------------
        # Update checkpoint candidate from the complete scrape
        # for this date BEFORE filtering old checkpoint records.
        # ---------------------------------------------------------
        if date_tenders:
            candidate_tender = None
            candidate_key = None

            for tender in reversed(date_tenders):
                key = get_tender_unique_key(tender)

                if key:
                    candidate_tender = tender
                    candidate_key = key
                    break

            if candidate_tender is not None and candidate_key:
                checkpoint_candidate = {
                    "last_date": current_date.strftime("%Y-%m-%d"),
                    "last_tender_key": candidate_key,
                }

        # ---------------------------------------------------------
        # Only filter already-processed tenders on the checkpoint
        # date.
        # ---------------------------------------------------------
        if (
            use_checkpoint
            and checkpoint_date
            and current_date.strftime("%Y-%m-%d") == checkpoint_date
            and checkpoint_key
        ):
            date_tenders = filter_checkpoint_tenders(
                tenders=date_tenders,
                checkpoint_date=checkpoint_date,
                checkpoint_key=checkpoint_key,
            )

        all_tenders.extend(date_tenders)

        current_date += timedelta(days=1)

    # ------------------------------------------------------
    # Deduplicate
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # Final result
    # ------------------------------------------------------

    print()
    print("=" * 70)
    print("PUNJAB PPRA - FINAL RESULT")
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

    return {
        "portal": PORTAL_NAME,
        "tenders": all_tenders,
        "checkpoint": checkpoint_candidate,
        "success": True,
    }


if __name__ == "__main__":

    result = scrape_punjab_tenders(
        start_date="2026-09-01",
        end_date="2026-09-24",
        use_checkpoint=True,
    )

    tenders = result.get("tenders", [])

    print()
    print("=" * 70)
    print("PUNJAB SCRAPING TEST")
    print("=" * 70)

    print(f"Success: {result['success']}")
    print(f"Tenders returned: {len(tenders)}")
    print(f"Checkpoint: {result['checkpoint']}")

    if tenders:
        print()
        print("FIRST RAW TENDER:")
        print(tenders[0])