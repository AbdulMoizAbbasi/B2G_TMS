import requests

from datetime import datetime, timedelta

from tender_scraper.storage.checkpoint import (
    get_checkpoint,
)


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = (
    "https://apiprd.eprocure.gov.pk/"
    "websiteportal/publicportal/1.0.0/api/v1/publicportal/"
    "getallpublictenders"
)

PORTAL_NAME = "Sindh PPRA"

PAGE_SIZE = "10"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "authorization": "Basic YWRtaW46cHByYTEy",
    "officedetail": "Sindh-PPRA-Dev",
}


# ============================================================
# SESSION
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    return session


# ============================================================
# FETCH ONE PAGE
# ============================================================

def fetch_page(
    session,
    date_of_advertisement,
    page_number=1,
):

    payload = {

        "pagination": {

            "pageNumber": str(
                page_number
            ),

            "pageSize": PAGE_SIZE,

            "orderBy": "",

            "orderByColumnName": "",

            "approvalStatusID": 0,

            "refTypeID": 0,
        },

        "filter": {

            "sortOrder": "",

            "activityStatus": None,

            "keywords": "",

            "tenderNo": "",

            "departmentName": None,

            "dateOfAdvertisement": (
                date_of_advertisement
            ),

            "closingDate": None,

            "selectedWorth": None,
        },

        "loggedInUserID": 1,

        "loggedInUserOfficeID": 31640,
    }

    response = session.post(
        API_URL,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# EXTRACT RAW RECORDS
# ============================================================

def extract_records(
    response_data,
):

    data = response_data.get(
        "data",
        {},
    )

    records = data.get(
        "records",
        [],
    )

    if not isinstance(
        records,
        list,
    ):
        return []

    #
    # Keep the original Sindh API
    # record structure.
    #
    # No normalization here.
    #

    return records


# ============================================================
# TOTAL PAGES
# ============================================================

def get_total_pages(
    response_data,
):

    data = response_data.get(
        "data",
        {},
    )

    total_pages = data.get(
        "totalPages",
        0,
    )

    try:

        return int(
            total_pages
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


# ============================================================
# UNIQUE TENDER KEY
# ============================================================

def get_tender_unique_key(
    tender,
):

    tender_number = tender.get(
        "tenderNumber"
    )

    if tender_number:

        return (
            "tenderNumber",
            str(
                tender_number
            ).strip(),
        )

    published_document_id = (
        tender.get(
            "publishedDocumentID"
        )
    )

    if published_document_id:

        return (
            "publishedDocumentID",
            str(
                published_document_id
            ).strip(),
        )

    return None


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_records(
    records,
):

    unique_records = []

    seen = set()

    duplicate_count = 0

    for tender in records:

        unique_key = (
            get_tender_unique_key(
                tender
            )
        )

        #
        # If no identifier exists,
        # keep the record.
        #

        if unique_key is None:

            unique_records.append(
                tender
            )

            continue

        if unique_key in seen:

            duplicate_count += 1

            continue

        seen.add(
            unique_key
        )

        unique_records.append(
            tender
        )

    if duplicate_count > 0:

        print(
            f"[{PORTAL_NAME}] "
            f"Removed duplicates: "
            f"{duplicate_count}"
        )

    return unique_records


# ============================================================
# PARSE PUBLISH DATE
# ============================================================

def parse_publish_datetime(
    tender,
):

    publish_date = tender.get(
        "publishDate"
    )

    if not publish_date:

        return datetime.min

    value = str(
        publish_date
    ).strip()

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for date_format in formats:

        try:

            return datetime.strptime(
                value,
                date_format,
            )

        except ValueError:

            continue

    #
    # Fallback
    #

    try:

        return datetime.strptime(
            value[:19],
            "%Y-%m-%dT%H:%M:%S",
        )

    except ValueError:

        return datetime.min


# ============================================================
# SORT TENDERS
# ============================================================

def sort_tenders(
    tenders,
):

    def sort_key(
        tender,
    ):

        publish_datetime = (
            parse_publish_datetime(
                tender
            )
        )

        tender_number = str(
            tender.get(
                "tenderNumber",
                "",
            )
        ).strip()

        return (
            publish_datetime,
            tender_number,
        )

    return sorted(
        tenders,
        key=sort_key,
    )


# ============================================================
# FILTER CHECKPOINT TENDERS
# ============================================================

def filter_checkpoint_tenders(
    tenders,
    checkpoint_date,
    checkpoint_key,
):

    #
    # No checkpoint key means there is
    # nothing to filter.
    #

    if not checkpoint_key:

        return tenders

    sorted_tenders = sort_tenders(
        tenders
    )

    checkpoint_index = None

    for index, tender in enumerate(
        sorted_tenders
    ):

        tender_key = tender.get(
            "tenderNumber"
        )

        if not tender_key:

            continue

        if str(
            tender_key
        ).strip() == str(
            checkpoint_key
        ).strip():

            checkpoint_index = index

            break

    #
    # Checkpoint tender not found.
    #
    # Be conservative and return all
    # records so that we don't risk
    # missing tenders.
    #

    if checkpoint_index is None:

        print()
        print(
            f"[{PORTAL_NAME}] "
            f"Checkpoint tender "
            f"{checkpoint_key} "
            f"was not found on "
            f"{checkpoint_date}."
        )

        print(
            f"[{PORTAL_NAME}] "
            f"Returning all tenders "
            f"for this date."
        )

        return sorted_tenders

    #
    # Everything after the checkpoint
    # is new.
    #

    new_tenders = (
        sorted_tenders[
            checkpoint_index + 1:
        ]
    )

    print()
    print(
        f"[{PORTAL_NAME}] "
        f"Checkpoint found: "
        f"{checkpoint_key}"
    )

    print(
        f"[{PORTAL_NAME}] "
        f"Tenders after checkpoint: "
        f"{len(new_tenders)}"
    )

    return new_tenders


# ============================================================
# BUILD CHECKPOINT CANDIDATE
# ============================================================

def build_checkpoint_candidate(
    tenders,
    current_date,
):

    if not tenders:

        return None

    #
    # Sindh API ordering is not reliable.
    # Determine the latest tender using
    # publishDate + tenderNumber.
    #

    sorted_tenders = sort_tenders(
        tenders
    )

    latest_tender = (
        sorted_tenders[-1]
    )

    tender_key = latest_tender.get(
        "tenderNumber"
    )

    if not tender_key:

        published_document_id = (
            latest_tender.get(
                "publishedDocumentID"
            )
        )

        if published_document_id:

            tender_key = str(
                published_document_id
            )

    if not tender_key:

        return None

    return {
        "last_date": current_date,
        "last_tender_key": str(
            tender_key
        ),
    }


# ============================================================
# SCRAPE ONE DATE
# ============================================================

def scrape_date(
    session,
    current_date,
):

    print()
    print(
        f"[{PORTAL_NAME}] "
        f"Fetching date: "
        f"{current_date}"
    )

    first_response = fetch_page(
        session=session,
        date_of_advertisement=current_date,
        page_number=1,
    )

    first_records = extract_records(
        first_response
    )

    total_pages = get_total_pages(
        first_response
    )

    print(
        f"[{PORTAL_NAME}] "
        f"{current_date} -> "
        f"{len(first_records)} records, "
        f"{total_pages} pages"
    )

    all_records = []

    all_records.extend(
        first_records
    )

    #
    # Fetch remaining pages.
    #

    for page_number in range(
        2,
        total_pages + 1,
    ):

        response = fetch_page(
            session=session,
            date_of_advertisement=current_date,
            page_number=page_number,
        )

        records = extract_records(
            response
        )

        print(
            f"[{PORTAL_NAME}] "
            f"{current_date} page "
            f"{page_number}/"
            f"{total_pages} -> "
            f"{len(records)} records"
        )

        all_records.extend(
            records
        )

    #
    # Remove duplicates across pages.
    #

    unique_records = (
        deduplicate_records(
            all_records
        )
    )

    print(
        f"[{PORTAL_NAME}] "
        f"{current_date} -> "
        f"{len(unique_records)} "
        f"unique records"
    )

    return unique_records


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_sindh_tenders(
    start_date=None,
    end_date=None,
    use_checkpoint=True,
):

    # --------------------------------------------------------
    # 1. LOAD CHECKPOINT
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

    # --------------------------------------------------------
    # 2. DETERMINE EFFECTIVE START DATE
    # --------------------------------------------------------

    if (
        use_checkpoint
        and checkpoint_date
    ):

        effective_start_date = (
            checkpoint_date
        )

        print()
        print(
            f"[{PORTAL_NAME}] "
            f"Checkpoint found."
        )

        print(
            f"Last date: "
            f"{checkpoint_date}"
        )

        print(
            f"Last tender key: "
            f"{checkpoint_key}"
        )

    else:

        if not start_date:

            raise ValueError(
                "start_date is required "
                "when no checkpoint exists."
            )

        effective_start_date = (
            start_date
        )

        print()
        print(
            f"[{PORTAL_NAME}] "
            f"No checkpoint found."
        )

        print(
            f"Using start date: "
            f"{effective_start_date}"
        )

    # --------------------------------------------------------
    # 3. END DATE
    # --------------------------------------------------------

    if not end_date:

        end_date = effective_start_date

    start = datetime.strptime(
        effective_start_date,
        "%Y-%m-%d",
    )

    end = datetime.strptime(
        end_date,
        "%Y-%m-%d",
    )

    if start > end:

        print()
        print(
            f"[{PORTAL_NAME}] "
            f"Start date is after end date."
        )

        return {
            "portal": PORTAL_NAME,
            "tenders": [],
            "checkpoint": None,
            "success": True,
        }

    # --------------------------------------------------------
    # 4. SCRAPE DATE BY DATE
    # --------------------------------------------------------

    session = create_session()

    all_tenders = []

    checkpoint_candidate = None

    current_date = start

    try:

        while current_date <= end:

            current_date_string = (
                current_date.strftime(
                    "%Y-%m-%d"
                )
            )

            #
            # IMPORTANT:
            #
            # First get the COMPLETE set
            # of tenders for this date.
            #

            scraped_date_tenders = (
                scrape_date(
                    session=session,
                    current_date=current_date_string,
                )
            )

            #
            # ------------------------------------------------
            # BUILD CHECKPOINT FROM COMPLETE DATE
            # ------------------------------------------------
            #
            # This happens BEFORE checkpoint
            # filtering.
            #
            # Therefore, if the checkpoint date
            # contains no newer tenders, we don't
            # lose the existing checkpoint.
            #

            candidate = (
                build_checkpoint_candidate(
                    tenders=scraped_date_tenders,
                    current_date=current_date_string,
                )
            )

            if candidate:

                #
                # Only advance the candidate if
                # this date is actually later than
                # the previous candidate date.
                #

                if (
                    checkpoint_candidate is None
                    or candidate["last_date"]
                    >= checkpoint_candidate[
                        "last_date"
                    ]
                ):

                    checkpoint_candidate = (
                        candidate
                    )

            #
            # ------------------------------------------------
            # CHECKPOINT FILTER
            # ------------------------------------------------
            #

            date_tenders = (
                scraped_date_tenders
            )

            if (
                use_checkpoint
                and checkpoint_date
                and current_date_string
                == checkpoint_date
            ):

                date_tenders = (
                    filter_checkpoint_tenders(
                        tenders=scraped_date_tenders,
                        checkpoint_date=checkpoint_date,
                        checkpoint_key=checkpoint_key,
                    )
                )

            #
            # Add only new/unprocessed
            # tenders to final result.
            #

            all_tenders.extend(
                date_tenders
            )

            current_date += timedelta(
                days=1
            )

    except Exception as error:

        print()
        print(
            f"[{PORTAL_NAME}] "
            f"Scraping failed."
        )

        print(
            f"Error: {error}"
        )

        return {
            "portal": PORTAL_NAME,
            "tenders": all_tenders,
            "checkpoint": None,
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # 5. FINAL DEDUPLICATION
    # --------------------------------------------------------

    all_tenders = (
        deduplicate_records(
            all_tenders
        )
    )

    # --------------------------------------------------------
    # 6. RESULT
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        f"[{PORTAL_NAME}] "
        f"Total unique tenders scraped: "
        f"{len(all_tenders)}"
    )

    if checkpoint_candidate:

        print(
            f"[{PORTAL_NAME}] "
            f"Checkpoint candidate:"
        )

        print(
            f"Last date: "
            f"{checkpoint_candidate['last_date']}"
        )

        print(
            f"Last tender key: "
            f"{checkpoint_candidate['last_tender_key']}"
        )

    else:

        print(
            f"[{PORTAL_NAME}] "
            f"No checkpoint candidate generated."
        )

    print(
        "=" * 70
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

    result = scrape_sindh_tenders(
        start_date="2026-09-15",
        end_date="2026-09-15",
        use_checkpoint=True,
    )

    print()
    print(
        "========== TEST RESULT =========="
    )

    print(
        "Success:",
        result.get(
            "success"
        ),
    )

    print(
        "Total unique tenders:",
        len(
            result.get(
                "tenders",
                [],
            )
        ),
    )

    print(
        "Checkpoint:",
        result.get(
            "checkpoint"
        ),
    )

    print()

    for tender in result.get(
        "tenders",
        [],
    )[:5]:

        print(
            tender
        )

        print(
            "-" * 70
        )