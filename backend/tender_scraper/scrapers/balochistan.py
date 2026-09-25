import json
from datetime import datetime
from urllib.parse import quote

import requests

from tender_scraper.storage.checkpoint import get_checkpoint


BASE_URL = "https://bpptest.vdc.solutions"
API_BASE_URL = "https://bpptwo.vdc.services:9446"
PORTAL_NAME = "Balochistan PPRA"

TENDER_ENDPOINT = (
    f"{API_BASE_URL}/api/LatestTenders/"
    "Get_AllTenderDNN/1/10/tenders/null/null//0//0//0//null/null/"
)


def parse_tender_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%Y-%m-%d",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    return None


def get_tender_key(tender):
    """
    Get the native Balochistan tender identifier.
    """
    return str(tender.get("TSENumber") or "").strip()


def build_model(date_from, date_to):
    return {
        "AgenciesArray": [],
        "ObjectArray": [],
        "ProcMethodArray": [],
        "DistrictArray": [],
        "DepartmentArray": [],
        "PSDPArray": [],
        "MinCost": 0,
        "MaxCost": 0,
        "YearId": 0,
        "From": date_from,
        "To": date_to,
    }


def fetch_page(page, model):
    encoded_model = quote(
        json.dumps(model, separators=(",", ":")),
        safe="",
    )

    url = (
        f"{API_BASE_URL}/api/LatestTenders/"
        f"Get_AllTenderDNN/"
        f"{page}/10/"
        f"tenders/null/null//0//0//0//null/null/"
        f"?model={encoded_model}"
    )

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected API response format.")

    tenders = data.get("Data")

    if tenders is None:
        tenders = data.get("tenders")

    if tenders is None:
        tenders = []

    if not isinstance(tenders, list):
        raise ValueError("Unexpected tender list format.")

    return tenders, data


def filter_checkpoint_tenders(tenders, checkpoint):
    """
    Balochistan returns tenders newest -> oldest.

    Newer date than checkpoint:
        keep

    Older date than checkpoint:
        discard

    Same date:
        keep records appearing before the checkpoint tender.

    Unknown dates:
        keep for safety.
    """

    if not checkpoint:
        return tenders

    last_date = checkpoint.get("last_date")
    last_tender_key = checkpoint.get("last_tender_key")

    if not last_date or not last_tender_key:
        return tenders

    checkpoint_date = parse_tender_date(last_date)

    if checkpoint_date is None:
        print(
            "Warning: Could not parse checkpoint date. "
            "Returning all tenders for safety."
        )
        return tenders

    checkpoint_position = None

    for index, tender in enumerate(tenders):
        tender_key = get_tender_key(tender)

        if tender_key == str(last_tender_key).strip():
            checkpoint_position = index
            break

    if checkpoint_position is None:
        print(
            "Warning: Checkpoint tender was not found in scraped results. "
            "Returning all tenders for safety."
        )
        return tenders

    filtered = []

    for index, tender in enumerate(tenders):
        tender_date = parse_tender_date(
            tender.get("PublishedDate")
        )

        if tender_date is None:
            filtered.append(tender)
            continue

        if tender_date > checkpoint_date:
            filtered.append(tender)

        elif tender_date == checkpoint_date:
            if index < checkpoint_position:
                filtered.append(tender)

    return filtered


def build_checkpoint_metadata(
    scraped_tenders,
    effective_date_from,
    date_to,
):
    """
    Balochistan returns newest -> oldest.

    The checkpoint represents the newest tender reached
    during the current scrape.
    """

    if not scraped_tenders:
        return None

    newest_date = None
    newest_index = None

    for index, tender in enumerate(scraped_tenders):
        tender_date = parse_tender_date(
            tender.get("PublishedDate")
        )

        if tender_date is None:
            continue

        if newest_date is None or tender_date > newest_date:
            newest_date = tender_date
            newest_index = index

    if newest_date is None or newest_index is None:
        return None

    newest_tender = scraped_tenders[newest_index]

    tender_key = get_tender_key(newest_tender)

    if not tender_key:
        return None

    return {
        "last_date": newest_date.strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),
        "last_tender_key": tender_key,
    }


def scrape_balochistan_tenders(
    date_from,
    date_to=None,
    use_checkpoint=True,
):
    if not date_from:
        raise ValueError("date_from cannot be empty.")

    if date_to is not None and not date_to:
        raise ValueError("date_to cannot be empty.")

    checkpoint = None

    if use_checkpoint:
        checkpoint = get_checkpoint(PORTAL_NAME)

        if (
            checkpoint.get("last_date")
            and checkpoint.get("last_tender_key")
        ):
            effective_date_from = checkpoint["last_date"]
        else:
            effective_date_from = date_from
    else:
        effective_date_from = date_from

    print(f"Portal: {PORTAL_NAME}")
    print(f"Use checkpoint: {use_checkpoint}")

    if checkpoint:
        print(
            f"Last date: "
            f"{checkpoint.get('last_date')}"
        )
        print(
            f"Last tender key: "
            f"{checkpoint.get('last_tender_key')}"
        )
    else:
        print("Last date: None")
        print("Last tender key: None")

    print(
        f"Requested start date: "
        f"{date_from}"
    )

    print(
        f"Effective start date: "
        f"{effective_date_from}"
    )

    print(f"End date: {date_to}")

    model = build_model(
        date_from=effective_date_from,
        date_to=date_to,
    )

    all_tenders = []

    page = 1

    while True:
        print(f"Fetching page {page}...")

        tenders, response_data = fetch_page(
            page=page,
            model=model,
        )

        if not tenders:
            print(
                f"Page {page}: No tenders"
            )
            break

        print(
            f"Page {page}: "
            f"{len(tenders)} tenders"
        )

        # Keep every tender exactly as returned by the API.
        all_tenders.extend(tenders)

        page += 1

    print(
        f"Tenders scraped: "
        f"{len(all_tenders)}"
    )

    checkpoint_metadata = build_checkpoint_metadata(
        scraped_tenders=all_tenders,
        effective_date_from=effective_date_from,
        date_to=date_to,
    )

    if checkpoint_metadata:
        print(
            "Checkpoint candidate date: "
            f"{checkpoint_metadata['last_date']}"
        )

        print(
            "Checkpoint candidate tender: "
            f"{checkpoint_metadata['last_tender_key']}"
        )
    else:
        print(
            "Checkpoint candidate: None"
        )

    # ---------------------------------------------------------
    # Checkpoint filtering is performed on the RAW API data.
    #
    # The checkpoint logic uses:
    #     PublishedDate
    #     TSENumber
    # ---------------------------------------------------------

    if use_checkpoint and checkpoint:
        filtered_tenders = filter_checkpoint_tenders(
            tenders=all_tenders,
            checkpoint=checkpoint,
        )
    else:
        filtered_tenders = all_tenders

    print(
        "Tenders returned after checkpoint: "
        f"{len(filtered_tenders)}"
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    #
    # Return the RAW API tender objects.
    #
    # No mapping.
    # No field renaming.
    # No field combining.
    # No fields removed.
    #
    # The downstream normalizer will add:
    #     id
    #     source
    #     relevance
    # ---------------------------------------------------------

    return {
        "portal": PORTAL_NAME,
        "tenders": filtered_tenders,
        "checkpoint": checkpoint_metadata,
    }


if __name__ == "__main__":
    result = scrape_balochistan_tenders(
        date_from="2026-09-22T00:00:00",
        date_to="2026-09-24T23:59:59",
        use_checkpoint=False,
    )

    print(f"\nTotal tenders: {len(result['tenders'])}")

    for tender in result["tenders"]:
        print(
            tender.get("TSENumber"),
            "|",
            tender.get("Id"),
            "|",
            tender.get("TenderName"),
            "|",
            tender.get("APP"),
            "|",
            tender.get("PType"),
        )