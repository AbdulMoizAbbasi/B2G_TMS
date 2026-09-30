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
    Filter Balochistan tenders using the checkpoint date only.

    Tenders newer than the checkpoint date:
        keep

    Tenders on the checkpoint date:
        keep

    Tenders older than the checkpoint date:
        discard

    Unknown dates:
        keep for safety.

    Tender number is intentionally not used as a checkpoint
    boundary. Existing tenders are handled by the database
    upsert logic.
    """

    if not checkpoint:
        return tenders

    last_date = checkpoint.get("last_date")

    if not last_date:
        return tenders

    checkpoint_date = parse_tender_date(
        last_date
    )

    if checkpoint_date is None:
        print(
            "Warning: Could not parse checkpoint date. "
            "Returning all tenders for safety."
        )
        return tenders

    filtered = []

    for tender in tenders:

        tender_date = parse_tender_date(
            tender.get("PublishedDate")
        )

        if tender_date is None:
            filtered.append(tender)
            continue

        if tender_date >= checkpoint_date:
            filtered.append(tender)

    return filtered


def build_checkpoint_metadata(
    scraped_tenders,
    effective_date_from,
    date_to,
):
    """
    Balochistan returns newest -> oldest.

    The checkpoint represents the newest tender date
    reached during the current scrape.

    Only the date is stored. Tender number is not used
    as a checkpoint boundary.
    """

    if not scraped_tenders:
        return None

    newest_date = None

    for tender in scraped_tenders:
        tender_date = parse_tender_date(
            tender.get("PublishedDate")
        )

        if tender_date is None:
            continue

        if newest_date is None or tender_date > newest_date:
            newest_date = tender_date

    if newest_date is None:
        return None

    return {
        "last_date": newest_date.strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),
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

        if checkpoint.get("last_date"):
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
    else:
        print("Last date: None")

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
    else:
        print(
            "Checkpoint candidate: None"
        )

    # ---------------------------------------------------------
    # Checkpoint filtering is date-based only.
    #
    # All tenders on the checkpoint date are kept.
    # Tender number is NOT used as a checkpoint boundary.
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