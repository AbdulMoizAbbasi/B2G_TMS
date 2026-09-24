import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from tender_scraper.storage.checkpoint import get_checkpoint


BASE_URL = "https://epms.ppra.gov.pk"
ACTIVE_TENDERS_URL = f"{BASE_URL}/public/tenders/active-tenders"
PORTAL_NAME = "Federal PPRA"

REQUEST_TIMEOUT = 30


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


def fetch_page(session, url, params=None):
    response = session.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.text


def clean_text(value):
    if value is None:
        return ""

    value = (
        value.get_text(" ", strip=True)
        if hasattr(value, "get_text")
        else str(value)
    )

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def make_absolute_url(url):
    if not url:
        return ""

    return urljoin(BASE_URL, url)


# ============================================================
# LISTING PAGE
# ============================================================

def extract_web_tender_no(row):
    cells = row.find_all("td")

    if len(cells) < 2:
        return ""

    value = clean_text(cells[1])

    if not value:
        return ""

    match = re.search(
        r"\bTS[A-Z0-9]+\b",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0)

    return value


def extract_detail_url(row):
    link = row.find("a", href=True)

    if not link:
        return ""

    href = link.get("href", "").strip()

    if not href:
        return ""

    return make_absolute_url(href)


def extract_listing_rows(soup):
    rows = []

    table = soup.find("table")

    if not table:
        return rows

    tbody = table.find("tbody")

    if tbody:
        candidate_rows = tbody.find_all("tr")
    else:
        candidate_rows = table.find_all("tr")

    for row in candidate_rows:

        cells = row.find_all("td")

        if not cells:
            continue

        web_tender_no = extract_web_tender_no(row)

        if not web_tender_no:
            continue

        detail_url = extract_detail_url(row)

        rows.append({
            "web_tender_no": web_tender_no,
            "detail_url": detail_url,
        })

    return rows


# ============================================================
# DETAIL PAGE
# ============================================================

def extract_detail_page_fields(soup):
    fields = {}

    for label_element in soup.select(".detail-label"):

        label = clean_text(label_element)

        if not label:
            continue

        label = label.rstrip(":")

        parent = label_element.parent

        if not parent:
            continue

        value_element = None

        for sibling in label_element.find_next_siblings():

            if sibling.name == "span":
                value_element = sibling
                break

        if value_element is None:

            spans = parent.find_all("span")

            for span in spans:

                if span == label_element:
                    continue

                value_element = span
                break

        if value_element is None:
            continue

        value = clean_text(value_element)

        if not value:
            continue

        fields[label] = value

    return fields


def extract_detail_page_title(soup):
    heading = soup.find("h1")

    if heading:
        title = clean_text(heading)

        if title:
            return title

    for tag_name in ("h2", "h3"):

        heading = soup.find(tag_name)

        if heading:
            title = clean_text(heading)

            if title:
                return title

    return ""


def extract_document_urls(soup):
    documents = []

    seen_urls = set()

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        if not href:
            continue

        if not href.startswith("/pdf?file="):
            continue

        document_url = make_absolute_url(href)

        if not document_url:
            continue

        if document_url in seen_urls:
            continue

        seen_urls.add(document_url)

        document_name = clean_text(link)

        if not document_name:
            document_name = "PDF Document"

        documents.append({
            "name": document_name,
            "url": document_url,
        })

    return documents


def extract_detail_page_tender(soup):
    fields = {}

    detail_fields = extract_detail_page_fields(soup)

    for key, value in detail_fields.items():
        fields[key] = value

    tender_title = extract_detail_page_title(soup)

    if tender_title:
        fields["Tender Title"] = tender_title

    documents = extract_document_urls(soup)

    if documents:
        fields["Documents"] = documents

    return fields


def fetch_tender_detail(session, detail_url):

    if not detail_url:
        return {}

    try:

        html = fetch_page(
            session,
            detail_url,
        )

    except requests.RequestException as exc:

        print(
            f"[Federal PPRA] Detail request failed: "
            f"{detail_url} | {exc}"
        )

        return {}

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return extract_detail_page_tender(soup)


def build_tender_from_listing(session, listing_tender):

    web_tender_no = listing_tender.get(
        "web_tender_no",
        "",
    )

    detail_url = listing_tender.get(
        "detail_url",
        "",
    )

    if not web_tender_no:
        return None

    detail_fields = fetch_tender_detail(
        session,
        detail_url,
    )

    tender = {
        "web_tender_no": web_tender_no,
        "detail_url": detail_url,
    }

    for key, value in detail_fields.items():
        tender[key] = value

    return tender


# ============================================================
# DEDUPLICATION
# ============================================================

def get_tender_key(tender):

    web_tender_no = str(
        tender.get(
            "web_tender_no",
            "",
        )
    ).strip()

    if web_tender_no:
        return web_tender_no

    detail_url = str(
        tender.get(
            "detail_url",
            "",
        )
    ).strip()

    if detail_url:
        return detail_url

    return ""


def deduplicate_tenders(tenders):

    unique_tenders = []

    seen = set()

    for tender in tenders:

        key = get_tender_key(tender)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        unique_tenders.append(tender)

    return unique_tenders


# ============================================================
# CHECKPOINT / LAST TENDER FILTER
# ============================================================

def filter_after_tender(
    tenders,
    last_tender_no,
):
    """
    Date filtering is already performed by the
    Federal PPRA portal.

    If last_tender_no is provided, return only
    tenders appearing after that tender in the
    date-filtered result.

    If last_tender_no is not provided, return
    all tenders from the requested date range.
    """

    if not last_tender_no:
        return tenders

    last_tender_no = str(
        last_tender_no
    ).strip()

    for index, tender in enumerate(tenders):

        key = get_tender_key(tender)

        if key == last_tender_no:

            return tenders[:index]

    print(
        "[Federal PPRA] Last tender number was not found "
        "inside the filtered result. Returning all "
        "scraped tenders."
    )

    return tenders


def build_checkpoint_candidate(
    tenders,
    previous_checkpoint,
):
    """
    Build the next checkpoint from the latest tender
    returned by the Federal portal.

    Checkpoint date is stored in YYYY-MM-DD because
    this is the exact format required by the Federal
    advertisement-date filter.
    """

    if not tenders:
        return previous_checkpoint

    last_tender = tenders[0]

    last_tender_key = get_tender_key(
        last_tender
    )

    if not last_tender_key:
        return previous_checkpoint

    advertised_date = (
        last_tender.get("Advertisement Date")
        or last_tender.get("advertised_date")
    )

    if not advertised_date:
        return previous_checkpoint

    advertised_date = str(
        advertised_date
    ).strip()

    parsed_date = None

    # Portal currently displays dates such as:
    # September 13, 2026

    try:

        parsed_date = datetime.strptime(
            advertised_date,
            "%B %d, %Y",
        )

    except ValueError:
        pass

    # Also support abbreviated month names.

    if parsed_date is None:

        try:

            parsed_date = datetime.strptime(
                advertised_date,
                "%b %d, %Y",
            )

        except ValueError:
            pass

    # If the detail page already gives YYYY-MM-DD,
    # preserve it directly.

    if parsed_date is None:

        try:

            parsed_date = datetime.strptime(
                advertised_date,
                "%Y-%m-%d",
            )

        except ValueError:
            pass

    if parsed_date is None:

        print(
            "[Federal PPRA] Could not determine "
            f"checkpoint date from: {advertised_date}"
        )

        return previous_checkpoint

    checkpoint_date = parsed_date.strftime(
        "%Y-%m-%d"
    )

    return {
        "last_date": checkpoint_date,
        "last_tender_key": str(
            last_tender_key
        ),
    }


# ============================================================
# PAGINATION
# ============================================================

def get_total_pages(soup):
    """
    Federal PPRA displays the pagination information
    directly on the page, for example:

        Page 1 of 26

    Read the total page count from that text instead
    of trying to infer it from pagination links.
    """

    # First try the exact element structure currently
    # used by the Federal PPRA portal.
    for element in soup.find_all("p"):

        text = clean_text(element)

        if not text:
            continue

        match = re.search(
            r"\bPage\s+\d+\s+of\s+(\d+)\b",
            text,
            flags=re.IGNORECASE,
        )

        if match:

            try:

                total_pages = int(
                    match.group(1)
                )

                if total_pages > 0:
                    return total_pages

            except ValueError:
                pass

    # Fallback: search the complete page text in case
    # the portal changes the containing HTML element.
    page_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    match = re.search(
        r"\bPage\s+\d+\s+of\s+(\d+)\b",
        page_text,
        flags=re.IGNORECASE,
    )

    if match:

        try:

            total_pages = int(
                match.group(1)
            )

            if total_pages > 0:
                return total_pages

        except ValueError:
            pass

    print(
        "[Federal PPRA] Could not detect total page "
        "count from portal. Assuming 1 page."
    )

    return 1


def build_page_params(
    page,
    date_from,
    date_to,
):
    """
    Build Federal PPRA active-tender filter.

    The portal fields are:

        advertise_date_from
        advertise_date_to
    """

    params = {
        "advertise_date_from": date_from,
        "advertise_date_to": date_to,
    }

    if page > 1:
        params["page"] = page

    return params


def fetch_tenders_page(
    session,
    page,
    date_from,
    date_to,
):

    params = build_page_params(
        page=page,
        date_from=date_from,
        date_to=date_to,
    )

    print(
        f"[Federal PPRA] Fetching listing page {page}"
    )

    print(
        f"[Federal PPRA] Advertise Date From: "
        f"{date_from}"
    )

    print(
        f"[Federal PPRA] Advertise Date To: "
        f"{date_to}"
    )

    try:

        html = fetch_page(
            session,
            ACTIVE_TENDERS_URL,
            params=params,
        )

    except requests.RequestException as exc:

        print(
            f"[Federal PPRA] Listing request failed: "
            f"{ACTIVE_TENDERS_URL} | {exc}"
        )

        return [], 0

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    listing_tenders = extract_listing_rows(
        soup
    )

    total_pages = get_total_pages(
        soup
    )

    return (
        listing_tenders,
        total_pages,
    )


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_federal_tenders(
    date_from=None,
    date_to=None,
    use_checkpoint=True,
):
    """
    Scrape Federal PPRA tenders incrementally.

    Checkpoint behavior:

    use_checkpoint=False:
        Ignore the existing checkpoint and use the
        supplied date_from/date_to.

    use_checkpoint=True:

        If no checkpoint exists:
            Use supplied date_from/date_to.

        If a checkpoint exists:
            Start from checkpoint last_date.
            Keep the supplied date_to.
            Fetch the complete checkpoint date because
            the Federal portal supports date-range filtering.
            Remove previously processed tenders using
            last_tender_key.

    IMPORTANT:

        This function does NOT update the checkpoint.

        The main pipeline must update the checkpoint
        only after successful downstream processing
        and storage.
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

    print(
        f"[Federal PPRA] Existing checkpoint: "
        f"{checkpoint}"
    )

    print(
        f"[Federal PPRA] Use checkpoint: "
        f"{use_checkpoint}"
    )

    # --------------------------------------------------------
    # DETERMINE EFFECTIVE DATE RANGE
    # --------------------------------------------------------

    effective_date_from = date_from
    effective_date_to = date_to
    last_tender_no = None

    if use_checkpoint and checkpoint_date:

        effective_date_from = checkpoint_date

        last_tender_no = checkpoint_key

        print(
            f"[Federal PPRA] Checkpoint found."
        )

        print(
            f"[Federal PPRA] Effective start date: "
            f"{effective_date_from}"
        )

        print(
            f"[Federal PPRA] Effective end date: "
            f"{effective_date_to}"
        )

        print(
            f"[Federal PPRA] Last tender number: "
            f"{last_tender_no}"
        )

    else:

        if use_checkpoint:

            print(
                "[Federal PPRA] No usable checkpoint "
                "found. Using configured date range."
            )

        print(
            f"[Federal PPRA] Advertise Date From: "
            f"{effective_date_from}"
        )

        print(
            f"[Federal PPRA] Advertise Date To: "
            f"{effective_date_to}"
        )

    if not effective_date_from:

        print(
            "[Federal PPRA] No advertise date from "
            "was provided."
        )

    if not effective_date_to:

        print(
            "[Federal PPRA] No advertise date to "
            "was provided."
        )

    session = create_session()

    all_listing_tenders = []

    # --------------------------------------------------------
    # FIRST PAGE
    # --------------------------------------------------------

    first_page_tenders, total_pages = (
        fetch_tenders_page(
            session=session,
            page=1,
            date_from=effective_date_from,
            date_to=effective_date_to,
        )
    )

    if not first_page_tenders and total_pages == 0:

        return {
            "portal": PORTAL_NAME,
            "tenders": [],
            "checkpoint": checkpoint_candidate,
            "success": False,
        }

    all_listing_tenders.extend(
        first_page_tenders
    )

    print(
        f"[Federal PPRA] Page 1: "
        f"{len(first_page_tenders)} listing tenders"
    )

    print(
        f"[Federal PPRA] Total pages detected: "
        f"{total_pages}"
    )

    # --------------------------------------------------------
    # REMAINING PAGES
    # --------------------------------------------------------

    for page in range(
        2,
        total_pages + 1,
    ):

        page_tenders, page_total_pages = (
            fetch_tenders_page(
                session=session,
                page=page,
                date_from=effective_date_from,
                date_to=effective_date_to,
            )
        )

        all_listing_tenders.extend(
            page_tenders
        )

        print(
            f"[Federal PPRA] Page {page}: "
            f"{len(page_tenders)} listing tenders"
        )

        # If the portal changes the total number of pages
        # while scraping, use the newest detected value.
        if page_total_pages > total_pages:

            total_pages = page_total_pages

            print(
                f"[Federal PPRA] Updated total pages: "
                f"{total_pages}"
            )

    # --------------------------------------------------------
    # DEDUPLICATE LISTING RESULTS
    # --------------------------------------------------------

    all_listing_tenders = (
        deduplicate_tenders(
            all_listing_tenders
        )
    )

    print(
        f"[Federal PPRA] Unique listing tenders: "
        f"{len(all_listing_tenders)}"
    )

    # --------------------------------------------------------
    # FETCH DETAIL PAGES
    # --------------------------------------------------------

    all_tenders = []

    for index, listing_tender in enumerate(
        all_listing_tenders,
        start=1,
    ):

        web_tender_no = listing_tender.get(
            "web_tender_no",
            "",
        )

        print(
            f"[Federal PPRA] Detail "
            f"{index}/{len(all_listing_tenders)}: "
            f"{web_tender_no}"
        )

        tender = build_tender_from_listing(
            session=session,
            listing_tender=listing_tender,
        )

        if tender is None:
            continue

        all_tenders.append(
            tender
        )

    # --------------------------------------------------------
    # DEDUPLICATE DETAILED TENDERS
    # --------------------------------------------------------

    all_tenders = deduplicate_tenders(
        all_tenders
    )

    print(
        f"[Federal PPRA] Unique detailed tenders: "
        f"{len(all_tenders)}"
    )

    # --------------------------------------------------------
    # LAST TENDER FILTER
    # --------------------------------------------------------

    new_tenders = filter_after_tender(
        all_tenders,
        last_tender_no,
    )

    print(
        f"[Federal PPRA] Tenders after last tender filter: "
        f"{len(new_tenders)}"
    )

    # --------------------------------------------------------
    # NEXT CHECKPOINT
    # --------------------------------------------------------

    checkpoint_candidate = (
        build_checkpoint_candidate(
            new_tenders,
            checkpoint_candidate,
        )
    )

    print(
        f"[Federal PPRA] Checkpoint candidate: "
        f"{checkpoint_candidate}"
    )

    return {
        "portal": PORTAL_NAME,
        "tenders": new_tenders,
        "checkpoint": checkpoint_candidate,
        "success": True,
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    import pprint

    result = scrape_federal_tenders(
        date_from="2026-09-10",
        date_to="2026-09-15",
        use_checkpoint=False,
    )

    pprint.pprint(
        result["tenders"][:5],
        sort_dicts=False,
        width=150,
    )