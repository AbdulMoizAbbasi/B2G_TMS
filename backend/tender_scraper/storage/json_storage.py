import json
from pathlib import Path


OUTPUT_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "relevant_tenders.json"
)
print(f"[Storage] Using file: {OUTPUT_FILE.resolve()}")

def load_relevant_tenders():
    """
    Load the existing master tender JSON.

    Returns:
        list: Existing tender records.
    """

    if not OUTPUT_FILE.exists():
        return []

    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return []

    if not isinstance(data, list):
        return []

    return data


def _save_json(tenders):
    """
    Atomically save tender records to the master JSON file.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = OUTPUT_FILE.with_suffix(
        ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            tenders,
            file,
            indent=4,
            ensure_ascii=False,
        )

    temporary_file.replace(
        OUTPUT_FILE
    )


def upsert_relevant_tenders(new_tenders):
    """
    Insert new tenders and update existing tenders
    using the tender's stable 'id' field.

    Existing records are preserved.

    Args:
        new_tenders (list):
            Newly processed relevant tender records.

    Returns:
        dict:
            Summary of the storage operation.
    """

    if not isinstance(
        new_tenders,
        list,
    ):
        raise ValueError(
            "new_tenders must be a list."
        )

    existing_tenders = load_relevant_tenders()

    tender_map = {}

    # Load existing records.
    for tender in existing_tenders:
        if not isinstance(
            tender,
            dict,
        ):
            continue

        tender_id = tender.get("id")

        if not tender_id:
            continue

        tender_map[str(tender_id)] = tender

    inserted = 0
    updated = 0

    # Insert or update new records.
    for tender in new_tenders:
        if not isinstance(
            tender,
            dict,
        ):
            continue

        tender_id = tender.get("id")

        if not tender_id:
            raise ValueError(
                "Every tender must contain a stable 'id'."
            )

        tender_id = str(tender_id)

        if tender_id in tender_map:
            tender_map[tender_id] = tender
            updated += 1
        else:
            tender_map[tender_id] = tender
            inserted += 1

    # Convert dictionary back to a list.
    merged_tenders = list(
        tender_map.values()
    )

    _save_json(
        merged_tenders
    )

    print()
    print(
        "RELEVANT TENDER STORAGE"
    )
    print(
        f"Existing records: {len(existing_tenders)}"
    )
    print(
        f"New records received: {len(new_tenders)}"
    )
    print(
        f"Inserted: {inserted}"
    )
    print(
        f"Updated: {updated}"
    )
    print(
        f"Total records: {len(merged_tenders)}"
    )
    print(
        f"File: {OUTPUT_FILE}"
    )

    return {
        "inserted": inserted,
        "updated": updated,
        "total": len(merged_tenders),
        "file": str(OUTPUT_FILE),
    }


def save_relevant_tenders(tenders):
    """
    Backward-compatible wrapper.

    This now performs a persistent upsert instead
    of overwriting the master JSON.
    """

    return upsert_relevant_tenders(
        tenders
    )


if __name__ == "__main__":
    print("=" * 70)
    print(
        "JSON STORAGE TEST"
    )
    print("=" * 70)

    test_tenders = [
        {
            "id": "test_portal_TEST001",
            "source": "Test Portal",
            "tender_number": "TEST001",
            "title": "Test Tender",
            "organization": "Test Organization",
            "advertised_date": "2026-09-09",
            "closing_date": "2026-09-20",
            "status": "Active",
            "tender_url": "https://example.com/test",
            "relevance": {
                "final_score": 0.85,
                "classification": "HIGH",
            },
            "other": {},
        }
    ]

    result = upsert_relevant_tenders(
        test_tenders
    )

    print()
    print(
        "Storage result:"
    )
    print(result)

    print()
    print("=" * 70)
    print(
        "JSON STORAGE TEST COMPLETE"
    )
    print("=" * 70)