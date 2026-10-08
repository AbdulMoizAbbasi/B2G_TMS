from datetime import datetime


from database.connection import SessionLocal


from tender_scraper.relevance.engine import analyze_tender


from tender_scraper.storage.normalizer import normalize_tender


from tender_scraper.storage.db_mapper import (
    map_punjab_tender,
    map_balochistan_tender,
)


from tender_scraper.storage.mysql_storage import persist_tender


from tender_scraper.storage.document_downloader import (
    download_document,
)


from tender_scraper.storage.checkpoint import (
    update_checkpoint,
)


PUNJAB_PORTAL = "Punjab PPRA"
BALOCHISTAN_PORTAL = "Balochistan PPRA"


# ============================================================
# CHECKPOINT HELPERS
# ============================================================


def get_latest_punjab_date(tenders):
    """
    Get the latest advertised_date from the raw
    Punjab tenders.

    Punjab format:
        "06 Oct 2026"

    Returns:
        YYYY-MM-DD string or None
    """

    latest_date = None

    for tender in tenders:

        value = tender.get(
            "advertised_date"
        )

        if not value:
            continue

        if isinstance(value, datetime):
            parsed_date = value.date()

        else:
            value = str(value).strip()

            if not value:
                continue

            try:
                parsed_date = datetime.strptime(
                    value,
                    "%d %b %Y",
                ).date()

            except ValueError:
                # Fallback for YYYY-MM-DD values
                try:
                    parsed_date = datetime.strptime(
                        value[:10],
                        "%Y-%m-%d",
                    ).date()

                except ValueError:
                    continue

        if (
            latest_date is None
            or parsed_date > latest_date
        ):
            latest_date = parsed_date

    if latest_date is None:
        return None

    return latest_date.strftime("%Y-%m-%d")


def get_latest_balochistan_date(tenders):
    """
    Get the latest PublishedDate from the raw
    Balochistan tenders.

    Balochistan returns UTC timestamps.

    The checkpoint is stored as a date-only value
    because the local runner expects:

        YYYY-MM-DD

    and constructs:

        YYYY-MM-DDT00:00:00

    Returns:
        YYYY-MM-DD string or None
    """

    latest_date = None

    for tender in tenders:

        value = tender.get(
            "PublishedDate"
        )

        if not value:
            continue

        value = str(value).strip()

        if not value:
            continue

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError:
            continue

        parsed_date = parsed.date()

        if (
            latest_date is None
            or parsed_date > latest_date
        ):
            latest_date = parsed_date

    if latest_date is None:
        return None

    return latest_date.strftime("%Y-%m-%d")


def update_punjab_checkpoint(tenders):
    """
    Update ECS Punjab checkpoint after
    successful processing.
    """

    latest_date = get_latest_punjab_date(
        tenders
    )

    if not latest_date:

        print(
            "[Punjab PPRA] No valid checkpoint date found."
        )

        return False, None

    update_checkpoint(
        portal=PUNJAB_PORTAL,
        last_date=latest_date,
    )

    print(
        f"[Punjab PPRA] Checkpoint updated: {latest_date}"
    )

    return True, latest_date


def update_balochistan_checkpoint(tenders):
    """
    Update ECS Balochistan checkpoint after
    successful processing.
    """

    latest_date = get_latest_balochistan_date(
        tenders
    )

    if not latest_date:

        print(
            "[Balochistan PPRA] No valid checkpoint date found."
        )

        return False, None

    update_checkpoint(
        portal=BALOCHISTAN_PORTAL,
        last_date=latest_date,
    )

    print(
        f"[Balochistan PPRA] Checkpoint updated: {latest_date}"
    )

    return True, latest_date


# ============================================================
# PUNJAB
# ============================================================


def process_local_punjab_tenders(tenders):
    """
    Process raw Punjab tenders received from the
    local scraper.

    The local scraper does NOT control the checkpoint.

    ECS processes and stores the tenders first.
    Only after successful processing is the ECS
    checkpoint updated.
    """

    if not isinstance(tenders, list):

        raise ValueError(
            "Punjab tenders must be a list."
        )

    print()
    print("=" * 70)
    print("LOCAL IMPORT - PUNJAB PPRA")
    print("=" * 70)

    print(
        f"Tenders received: {len(tenders)}"
    )

    if not tenders:

        return {
            "success": True,
            "portal": PUNJAB_PORTAL,
            "scraped": 0,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "relevant": 0,
            "irrelevant": 0,
            "checkpoint_updated": False,
            "checkpoint_date": None,
        }

    processed_tenders = []

    # --------------------------------------------------------
    # 1. Relevance + normalization
    # --------------------------------------------------------

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis.get(
            "relevance",
            {},
        )

        normalized = normalize_tender(
            tender=tender,
            portal=PUNJAB_PORTAL,
            relevance=relevance,
        )

        processed_tenders.append(
            normalized
        )

    relevant_count = sum(
        1
        for tender in processed_tenders
        if tender.get(
            "relevance",
            {},
        ).get(
            "keyword_score",
            0,
        ) > 0
    )

    # --------------------------------------------------------
    # 2. Persist ALL tenders
    # --------------------------------------------------------

    db = SessionLocal()

    processed_count = 0
    created_count = 0
    updated_count = 0

    try:

        for tender in processed_tenders:

            mapped_tender = map_punjab_tender(
                tender=tender,
                relevance_result={
                    "relevance": tender.get(
                        "relevance",
                        {},
                    )
                },
            )

            relevance = tender.get(
                "relevance",
                {},
            )

            keyword_score = relevance.get(
                "keyword_score",
                0,
            )

            # ------------------------------------------------
            # Download primary document only for relevant
            # tenders
            # ------------------------------------------------

            if keyword_score > 0:

                documents = mapped_tender.get(
                    "documents",
                    [],
                )

                for document in documents:

                    source_url = document.get(
                        "source_url"
                    )

                    if not source_url:
                        continue

                    download_result = download_document(
                        source_url,
                        source=PUNJAB_PORTAL,
                        tender_key=tender.get(
                            "id"
                        ),
                        document_name=(
                            "bidding_document.pdf"
                        ),
                    )

                    document.update(
                        download_result
                    )

            # ------------------------------------------------
            # Persist
            # ------------------------------------------------

            persist_result = persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=relevance,
            )

            action = persist_result[
                "action"
            ]

            processed_count += 1

            if action == "CREATED":
                created_count += 1

            elif action == "UPDATED":
                updated_count += 1

    except Exception:

        db.rollback()

        # IMPORTANT:
        # No checkpoint update occurs here.
        raise

    finally:

        db.close()

    irrelevant_count = (
        len(tenders) - relevant_count
    )

    # --------------------------------------------------------
    # 3. Update ECS checkpoint ONLY AFTER successful DB
    #    processing
    # --------------------------------------------------------

    checkpoint_updated, checkpoint_date = (
        update_punjab_checkpoint(
            tenders
        )
    )

    print()
    print("-" * 70)
    print("LOCAL PUNJAB PPRA SUMMARY")
    print("-" * 70)

    print(
        f"Tenders fetched:    {len(tenders)}"
    )

    print(
        f"Tenders processed:  {processed_count}"
    )

    print(
        f"Created:             {created_count}"
    )

    print(
        f"Updated:             {updated_count}"
    )

    print(
        f"Relevant:            {relevant_count}"
    )

    print(
        f"Irrelevant:          {irrelevant_count}"
    )

    print(
        f"Checkpoint updated:  {checkpoint_updated}"
    )

    if checkpoint_date:

        print(
            f"Checkpoint date:     {checkpoint_date}"
        )

    return {
        "success": True,
        "portal": PUNJAB_PORTAL,
        "scraped": len(tenders),
        "processed": processed_count,
        "created": created_count,
        "updated": updated_count,
        "relevant": relevant_count,
        "irrelevant": irrelevant_count,
        "checkpoint_updated": checkpoint_updated,
        "checkpoint_date": checkpoint_date,
    }


# ============================================================
# BALOCHISTAN
# ============================================================


def process_local_balochistan_tenders(tenders):
    """
    Process raw Balochistan tenders received from
    the local scraper.

    The local scraper does NOT control the checkpoint.

    ECS processes and stores the tenders first.
    Only after successful processing is the ECS
    checkpoint updated.
    """

    if not isinstance(tenders, list):

        raise ValueError(
            "Balochistan tenders must be a list."
        )

    print()
    print("=" * 70)
    print("LOCAL IMPORT - BALOCHISTAN PPRA")
    print("=" * 70)

    print(
        f"Tenders received: {len(tenders)}"
    )

    if not tenders:

        return {
            "success": True,
            "portal": BALOCHISTAN_PORTAL,
            "scraped": 0,
            "processed": 0,
            "created": 0,
            "updated": 0,
            "relevant": 0,
            "irrelevant": 0,
            "checkpoint_updated": False,
            "checkpoint_date": None,
        }

    relevant_count = 0
    processed_count = 0
    created_count = 0
    updated_count = 0

    db = SessionLocal()

    try:

        for index, tender in enumerate(
            tenders,
            start=1,
        ):

            # ------------------------------------------------
            # 1. Relevance analysis
            # ------------------------------------------------

            analysis = analyze_tender(
                tender
            )

            relevance = analysis.get(
                "relevance",
                {},
            )

            keyword_score = relevance.get(
                "keyword_score",
                0,
            )

            if keyword_score > 0:
                relevant_count += 1

            # ------------------------------------------------
            # 2. Normalize
            # ------------------------------------------------

            normalized = normalize_tender(
                tender=tender,
                portal=BALOCHISTAN_PORTAL,
                relevance=relevance,
            )

            # ------------------------------------------------
            # 3. Map
            # ------------------------------------------------

            mapped_tender = map_balochistan_tender(
                tender=normalized,
                relevance_result=analysis,
            )

            # ------------------------------------------------
            # 4. Download primary document only for relevant
            # ------------------------------------------------

            if keyword_score > 0:

                documents = mapped_tender.get(
                    "documents",
                    [],
                )

                for document in documents:

                    source_url = document.get(
                        "source_url"
                    )

                    if not source_url:
                        continue

                    tender_key = (
                        tender.get(
                            "TSENumber"
                        )
                        or str(
                            tender.get(
                                "Id"
                            )
                        )
                    )

                    download_result = download_document(
                        source_url,
                        source=BALOCHISTAN_PORTAL,
                        tender_key=tender_key,
                        document_name="Bidding Document",
                    )

                    document.update(
                        download_result
                    )

            # ------------------------------------------------
            # 5. Persist
            # ------------------------------------------------

            persist_result = persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=relevance,
            )

            action = persist_result[
                "action"
            ]

            processed_count += 1

            if action == "CREATED":
                created_count += 1

            elif action == "UPDATED":
                updated_count += 1

    except Exception:

        db.rollback()

        # IMPORTANT:
        # No checkpoint update occurs here.
        raise

    finally:

        db.close()

    irrelevant_count = (
        len(tenders) - relevant_count
    )

    # --------------------------------------------------------
    # 6. Update ECS checkpoint ONLY AFTER successful DB
    #    processing
    # --------------------------------------------------------

    checkpoint_updated, checkpoint_date = (
        update_balochistan_checkpoint(
            tenders
        )
    )

    print()
    print("-" * 70)
    print("LOCAL BALOCHISTAN PPRA SUMMARY")
    print("-" * 70)

    print(
        f"Tenders fetched:    {len(tenders)}"
    )

    print(
        f"Tenders processed:  {processed_count}"
    )

    print(
        f"Created:             {created_count}"
    )

    print(
        f"Updated:             {updated_count}"
    )

    print(
        f"Relevant:            {relevant_count}"
    )

    print(
        f"Irrelevant:          {irrelevant_count}"
    )

    print(
        f"Checkpoint updated:  {checkpoint_updated}"
    )

    if checkpoint_date:

        print(
            f"Checkpoint date:     {checkpoint_date}"
        )

    return {
        "success": True,
        "portal": BALOCHISTAN_PORTAL,
        "scraped": len(tenders),
        "processed": processed_count,
        "created": created_count,
        "updated": updated_count,
        "relevant": relevant_count,
        "irrelevant": irrelevant_count,
        "checkpoint_updated": checkpoint_updated,
        "checkpoint_date": checkpoint_date,
    }