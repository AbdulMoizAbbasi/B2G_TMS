from datetime import datetime
from tender_scraper.scrapers.kp import scrape_kp_tenders
from tender_scraper.scrapers.federal import scrape_federal_tenders
from tender_scraper.scrapers.punjab import scrape_punjab_tenders
from tender_scraper.scrapers.balochistan import scrape_balochistan_tenders
from tender_scraper.scrapers.sindh import scrape_sindh_tenders

from tender_scraper.relevance.engine import analyze_tender

from tender_scraper.storage.json_storage import (
    upsert_relevant_tenders,
)

from tender_scraper.storage.normalizer import (
    normalize_tender,
)

from tender_scraper.storage.checkpoint import (
    update_checkpoint,
)

from database.connection import SessionLocal

from tender_scraper.storage.db_mapper import (
    map_federal_tender,
    map_punjab_tender,
    map_kp_tender,
    map_balochistan_tender,
    map_sindh_tender,
)

from tender_scraper.storage.mysql_storage import (
    persist_tender,
)

from tender_scraper.storage.document_downloader import (
    download_document,
    get_sindh_document_metadata,
    download_sindh_document,
)

# ============================================================
# CONFIGURATION
# ============================================================

FEDERAL_PORTAL = "Federal PPRA"
PUNJAB_PORTAL = "Punjab PPRA"
BALOCHISTAN_PORTAL = "Balochistan PPRA"
KP_PORTAL = "KP PPRA"
SINDH_PORTAL = "Sindh PPRA"


# ============================================================
# DATE CONFIGURATION
# ============================================================

#
# These are ONLY used when no checkpoint exists.
#

FEDERAL_INITIAL_START_DATE = "2026-09-01"
PUNJAB_INITIAL_START_DATE = "2026-09-01"
KP_INITIAL_START_DATE = "2026-09-01"
SINDH_INITIAL_START_DATE = "2026-09-01"


#
# Balochistan API expects UTC ISO timestamps.
#
# Pakistan time:
# 2026-09-01 00:00
# =
# 2026-08-31 19:00 UTC
#

BALOCHISTAN_INITIAL_START_DATE = (
    "2026-08-31T19:00:00.000Z"
)


#
# Always scrape up to today.
#

TODAY = datetime.today().strftime(
    "%Y-%m-%d"
)

FEDERAL_END_DATE = TODAY
PUNJAB_END_DATE = TODAY
KP_END_DATE = TODAY
SINDH_END_DATE = TODAY

#
# Balochistan end date:
#
# Today at 00:00 Pakistan time
# =
# Previous day at 19:00 UTC
#

BALOCHISTAN_END_DATE = (
    datetime.strptime(
        TODAY,
        "%Y-%m-%d",
    ).strftime(
        "%Y-%m-%dT19:00:00.000Z"
    )
)


# ============================================================
# HELPER
# ============================================================

def update_checkpoint_from_result(
    portal,
    result,
):
    """
    Update a portal checkpoint using checkpoint metadata
    returned by the scraper.

    The scraper does NOT save the checkpoint itself.

    Checkpoint is updated only after:

        scrape
        -> relevance
        -> normalization
        -> persistent storage

    have completed successfully.
    """

    checkpoint = result.get(
        "checkpoint"
    )

    if not isinstance(
        checkpoint,
        dict,
    ):

        print()
        print(
            f"[{portal}] No checkpoint metadata returned."
        )

        print(
            f"[{portal}] Checkpoint was NOT updated."
        )

        return False

    last_date = checkpoint.get(
        "last_date"
    )

    last_tender_key = checkpoint.get(
        "last_tender_key"
    )

    if not last_date or not last_tender_key:

        print()
        print(
            f"[{portal}] Incomplete checkpoint metadata."
        )

        print(
            f"[{portal}] Checkpoint was NOT updated."
        )

        return False

    update_checkpoint(
        portal=portal,
        last_date=last_date,
        last_tender_key=last_tender_key,
    )

    print()
    print(
        f"[{portal}] Checkpoint updated."
    )

    print(
        f"Last date: {last_date}"
    )

    print(
        f"Last tender key: {last_tender_key}"
    )

    return True


# ============================================================
# FEDERAL PPRA
# ============================================================

def process_federal():

    print()
    print("=" * 70)
    print("FEDERAL PPRA")
    print("=" * 70)

    print(
        f"Initial fallback date: "
        f"{FEDERAL_INITIAL_START_DATE}"
    )

    print(
        f"Scrape end date: "
        f"{FEDERAL_END_DATE}"
    )

    # --------------------------------------------------------
    # 1. Scrape
    # --------------------------------------------------------

    result = scrape_federal_tenders(
        date_from=FEDERAL_INITIAL_START_DATE,
        date_to=FEDERAL_END_DATE,
        use_checkpoint=True,
    )

    tenders = result.get(
        "tenders",
        [],
    )

    print()
    print(
        f"[Federal PPRA] Tenders received: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "[Federal PPRA] No tenders to process."
        )

        return {
            "success": True,
            "scraped": 0,
            "Processed": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    processed_tenders = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        normalized = normalize_tender(
            tender=tender,
            portal=FEDERAL_PORTAL,
            relevance=relevance,
        )

        processed_tenders.append(
            normalized
        )
    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("FEDERAL RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Processed:       {len(processed_tenders)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        stored_count = 0

        for tender in processed_tenders:

            mapped_tender = map_federal_tender(
                tender=tender,
                relevance_result={
                    "relevance": tender.get(
                        "relevance",
                        {},
                    )
                },
            )

            # ----------------------------------------------------
            # Download primary document
            # ----------------------------------------------------

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
                    source=FEDERAL_PORTAL,
                    tender_key=tender.get(
                        "web_tender_no"
                    ) or tender.get(
                        "id"
                    ),
                    document_name="tender_document.pdf",
                )

                document.update(
                    download_result
                )

            # ----------------------------------------------------
            # Persist tender + relevance + documents
            # ----------------------------------------------------

            persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=tender.get(
                    "relevance",
                    {},
                ),
            )

            stored_count += 1

    finally:

        db.close()

    # --------------------------------------------------------
    # 5. Update checkpoint
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=FEDERAL_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show relevant tenders
    # --------------------------------------------------------

    print()
    print(
        "FEDERAL PPRA - TOP RELEVANT TENDERS"
    )

    print("=" * 70)

    for tender in processed_tenders[:10]:

        relevance = tender.get(
            "relevance",
            {},
        )

        print()
        print("Tender ID:")
        print(
            tender.get(
                "id",
                "N/A",
            )
        )

        print("Title:")
        print(
            tender.get(
                "Tender Title",
                "",
            )
        )

        print("Keyword Score:")
        print(
            relevance.get(
                "keyword_score",
                0,
            )
        )

        print("Matched Keywords:")
        print(
            relevance.get(
                "matched_keywords",
                [],
            )
        )

        print("Matched Capabilities:")
        print(
            relevance.get(
                "matched_capabilities",
                [],
            )
        )

        print("Tender URL:")
        print(
            tender.get(
                "detail_url",
                "",
            )
            or "N/A"
        )

        print("-" * 70)

    return {
        "success": True,
        "scraped": len(tenders),
        "processed": len(processed_tenders),
        "checkpoint_updated": checkpoint_updated,
    }


# ============================================================
# PUNJAB PPRA
# ============================================================

def process_punjab():

    print()
    print("=" * 70)
    print("PUNJAB PPRA")
    print("=" * 70)

    print(
        f"Initial fallback date: "
        f"{PUNJAB_INITIAL_START_DATE}"
    )

    print(
        f"Scrape end date: "
        f"{PUNJAB_END_DATE}"
    )

    # --------------------------------------------------------
    # 1. Scrape
    # --------------------------------------------------------

    result = scrape_punjab_tenders(
        start_date=PUNJAB_INITIAL_START_DATE,
        end_date=PUNJAB_END_DATE,
        use_checkpoint=True,
    )

    tenders = result.get(
        "tenders",
        [],
    )

    print()
    print(
        f"[Punjab PPRA] Tenders received: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "[Punjab PPRA] No tenders to process."
        )

        return {
            "success": True,
            "scraped": 0,
            "processed": 0,
            "stored": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    processed_tenders = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        normalized = normalize_tender(
            tender=tender,
            portal=PUNJAB_PORTAL,
            relevance=relevance,
        )

        processed_tenders.append(
            normalized
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

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

    print()
    print("-" * 70)
    print("PUNJAB RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Relevant:   {relevant_count}"
    )

    print(
        f"Irrelevant: "
        f"{len(tenders) - relevant_count}"
    )

    # --------------------------------------------------------
    # 4. Persist ALL tenders to MySQL
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        stored_count = 0

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

                download_result = (
                    download_document(
                        source_url,
                        source=PUNJAB_PORTAL,
                        tender_key=(tender.get("id")),
                        document_name=(
                            "bidding_document.pdf"
                        ),
                    )
                )

                document.update(
                    download_result
                )

            persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=tender.get(
                    "relevance",
                    {},
                ),
            )

            stored_count += 1

    finally:

        db.close()

    # --------------------------------------------------------
    # 5. Update checkpoint
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=PUNJAB_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show processed tenders
    # --------------------------------------------------------

    print()
    print(
        "PUNJAB PPRA - FIRST PROCESSED TENDERS"
    )

    print("=" * 70)

    for tender in processed_tenders[:10]:

        relevance = tender.get(
            "relevance",
            {},
        )

        print()
        print("Tender ID:")
        print(
            tender.get(
                "id",
                "N/A",
            )
        )

        print("Title:")
        print(
            tender.get(
                "tender_details",
                "",
            )
        )

        print("Keyword Score:")
        print(
            relevance.get(
                "keyword_score",
                0,
            )
        )

        print("Matched Keywords:")
        print(
            relevance.get(
                "matched_keywords",
                [],
            )
        )

        print("Bidding Document URL:")
        print(
            tender.get(
                "bidding_document_url",
                "",
            )
            or "N/A"
        )

        print("-" * 70)

    return {
        "success": True,
        "scraped": len(tenders),
        "processed": len(processed_tenders),
        "stored": stored_count,
        "checkpoint_updated": checkpoint_updated,
    }


# ============================================================
# BALOCHISTAN PPRA
# ============================================================

def process_balochistan():

    print()
    print("=" * 70)
    print("BALOCHISTAN PPRA")
    print("=" * 70)

    print(
        f"Initial fallback date: "
        f"{BALOCHISTAN_INITIAL_START_DATE}"
    )

    print(
        f"Scrape end date: "
        f"{BALOCHISTAN_END_DATE}"
    )

    # --------------------------------------------------------
    # 1. Scrape
    # --------------------------------------------------------

    result = scrape_balochistan_tenders(
        date_from=BALOCHISTAN_INITIAL_START_DATE,
        date_to=BALOCHISTAN_END_DATE,
    )

    tenders = result.get(
        "tenders",
        [],
    )

    print()
    print(
        f"[Balochistan PPRA] Tenders received: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "[Balochistan PPRA] No tenders to process."
        )

        return {
            "success": True,
            "scraped": 0,
            "processed": 0,
            "relevant": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Analyze + normalize + map + persist ALL tenders
    # --------------------------------------------------------

    relevant_count = 0
    processed_count = 0

    db = SessionLocal()

    try:

        for index, tender in enumerate(
            tenders,
            start=1,
        ):

            print()
            print(
                f"[Balochistan PPRA] "
                f"Processing {index}/{len(tenders)}"
            )

            # ------------------------------------------------
            # Relevance analysis
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
            # Normalize
            # ------------------------------------------------

            normalized = normalize_tender(
                tender=tender,
                portal=BALOCHISTAN_PORTAL,
                relevance=relevance,
            )

            # ------------------------------------------------
            # Map to DB structure
            # ------------------------------------------------

            mapped_tender = map_balochistan_tender(
                tender=normalized,
                relevance_result=analysis,
            )

            # ------------------------------------------------
            # Download primary document
            # ------------------------------------------------

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
                    tender.get("TSENumber")
                    or str(tender.get("Id"))
                )

                download_result = download_document(
                    source_url,
                    source="Balochistan PPRA",
                    tender_key=tender_key,
                    document_name="Bidding Document",
                )

                document.update(
                    download_result
                )

            # ------------------------------------------------
            # Persist ALL tenders
            # ------------------------------------------------

            persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=relevance,
            )

            processed_count += 1

            print(
                f"[Balochistan PPRA] "
                f"Stored jazzid for "
                f"{tender.get('TSENumber', 'N/A')} "
                f"| Score: {keyword_score}"
            )

        # ----------------------------------------------------
        # 3. Commit all successful processing
        # ----------------------------------------------------

        # persist_tender() commits internally.
        # Reaching this point means all processed records
        # were successfully persisted.

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()

    # --------------------------------------------------------
    # 4. Relevance summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("BALOCHISTAN RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Processed:  {processed_count}"
    )

    print(
        f"Relevant:   {relevant_count}"
    )

    print(
        f"Irrelevant: "
        f"{len(tenders) - relevant_count}"
    )

    # --------------------------------------------------------
    # 5. Update checkpoint ONLY after DB persistence
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=BALOCHISTAN_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Return
    # --------------------------------------------------------

    return {
        "success": True,
        "scraped": len(tenders),
        "processed": processed_count,
        "relevant": relevant_count,
        "checkpoint_updated": checkpoint_updated,
    }
# ============================================================
# KP PPRA
# ============================================================

def process_kp():

    print()
    print("=" * 70)
    print("KP PPRA")
    print("=" * 70)

    print(
        f"Initial fallback date: "
        f"{KP_INITIAL_START_DATE}"
    )

    print(
        f"Scrape end date: "
        f"{KP_END_DATE}"
    )

    # --------------------------------------------------------
    # 1. Scrape
    # --------------------------------------------------------

    result = scrape_kp_tenders(
        start_date=KP_INITIAL_START_DATE,
        end_date=KP_END_DATE,
        use_checkpoint=True,
    )

    tenders = result.get(
        "tenders",
        [],
    )

    print()
    print(
        f"[KP PPRA] Tenders received: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "[KP PPRA] No tenders to process."
        )

        return {
            "success": True,
            "scraped": 0,
            "processed": 0,
            "relevant": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Analyze + normalize ALL tenders
    # --------------------------------------------------------

    analyzed_tenders = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        normalized = normalize_tender(
            tender=tender,
            portal=KP_PORTAL,
            relevance=relevance,
        )

        analyzed_tenders.append(
            {
                "tender": tender,
                "normalized": normalized,
                "relevance": relevance,
            }
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    relevant_count = sum(
        1
        for item in analyzed_tenders
        if item["relevance"].get(
            "keyword_score",
            0,
        ) > 0
    )

    print()
    print("-" * 70)
    print("KP RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Relevant:   {relevant_count}"
    )

    print(
        f"Irrelevant: "
        f"{len(tenders) - relevant_count}"
    )

    # --------------------------------------------------------
    # 4. Persist ALL tenders
    # --------------------------------------------------------

    db = SessionLocal()

    processed = 0

    try:

        for item in analyzed_tenders:

            tender = item["tender"]
            normalized = item["normalized"]
            relevance = item["relevance"]

            # ------------------------------------------------
            # Map normalized fields to DB structure
            # ------------------------------------------------

            mapped_tender = map_kp_tender(
                tender=tender,
                relevance_result={
                    "relevance": relevance,
                },
            )

            # ------------------------------------------------
            # Download primary bidding document
            # ------------------------------------------------

            documents = mapped_tender.get(
                "documents",
                [],
            )

            for document in documents:

                download_result = (
                    download_document(
                        url=document.get(
                            "source_url"
                        ),
                        source=KP_PORTAL,
                        tender_key=tender.get(
                            "id"
                        )
                        or tender.get(
                            "tender_number"
                        ),
                        document_name=document.get(
                            "document_name"
                        ),
                    )
                )

                document.update(
                    download_result
                )

            # ------------------------------------------------
            # Persist tender + relevance + documents
            # ------------------------------------------------

            persist_tender(
                db=db,
                mapped_tender=mapped_tender,
                relevance=relevance,
            )

            processed += 1

            print(
                f"[KP PPRA] Stored "
                f"{processed}/{len(analyzed_tenders)}: "
                f"{tender.get('tender_number', 'N/A')}"
            )

    finally:

        db.close()

    # --------------------------------------------------------
    # 5. Update checkpoint ONLY after persistence succeeds
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=KP_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show processed tenders
    # --------------------------------------------------------

    print()
    print(
        "KP PPRA - PROCESSED TENDERS"
    )

    print("=" * 70)

    for item in analyzed_tenders[:10]:

        tender = item["tender"]
        relevance = item["relevance"]

        print()
        print("Tender Number:")
        print(
            tender.get(
                "tender_number",
                "",
            )
            or "N/A"
        )

        print("Title:")
        print(
            tender.get(
                "tender_details",
                "",
            )
        )

        print("Keyword Score:")
        print(
            relevance.get(
                "keyword_score",
                0,
            )
        )

        print("Matched Keywords:")
        print(
            relevance.get(
                "matched_keywords",
                [],
            )
        )

        print("Matched Capabilities:")
        print(
            relevance.get(
                "matched_capabilities",
                [],
            )
        )

        print("Bidding Document:")
        print(
            tender.get(
                "bidding_document_url",
                "",
            )
            or "N/A"
        )

        print("-" * 70)

    return {
        "success": True,
        "scraped": len(tenders),
        "processed": processed,
        "relevant": relevant_count,
        "checkpoint_updated": checkpoint_updated,
    }

# ============================================================
# SINDH PPRA
# ============================================================

def process_sindh():

    print()
    print("=" * 70)
    print("SINDH PPRA")
    print("=" * 70)

    print(
        f"Initial fallback date: "
        f"{SINDH_INITIAL_START_DATE}"
    )

    print(
        f"Scrape end date: "
        f"{SINDH_END_DATE}"
    )

    # --------------------------------------------------------
    # 1. Scrape
    # --------------------------------------------------------

    result = scrape_sindh_tenders(
        start_date=SINDH_INITIAL_START_DATE,
        end_date=SINDH_END_DATE,
        use_checkpoint=True,
    )

    tenders = result.get(
        "tenders",
        [],
    )

    print()
    print(
        f"[Sindh PPRA] Tenders received: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "[Sindh PPRA] No tenders to process."
        )

        return {
            "success": True,
            "scraped": 0,
            "processed": 0,
            "relevant": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Database session
    # --------------------------------------------------------

    db = SessionLocal()

    processed = 0
    relevant_count = 0

    try:

        # ----------------------------------------------------
        # 3. Process ALL tenders
        # ----------------------------------------------------

        for index, tender in enumerate(
            tenders,
            start=1,
        ):

            print()
            print(
                f"[Sindh PPRA] Processing "
                f"{index}/{len(tenders)}"
            )

            # -----------------------------------------------
            # Relevance analysis
            # -----------------------------------------------

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

            # -----------------------------------------------
            # Normalize
            # -----------------------------------------------

            normalized = normalize_tender(
                tender=tender,
                portal=SINDH_PORTAL,
                relevance=relevance,
            )

            # -----------------------------------------------
            # Map to database structure
            # -----------------------------------------------

            mapped_tender = map_sindh_tender(
                tender=normalized,
                relevance_result=analysis,
            )

            # -----------------------------------------------
            # Download primary document
            # -----------------------------------------------

            published_document_id = tender.get(
                "publishedDocumentID"
            )

            documents = mapped_tender.get(
                "documents",
                [],
            )

            if published_document_id:

                print(
                    "[Sindh PPRA] Fetching "
                    "document metadata..."
                )

                try:

                    document_metadata = (
                        get_sindh_document_metadata(
                            published_document_id
                        )
                    )

                    if document_metadata:

                        file_id = document_metadata.get(
                            "file_id"
                        )

                        file_guid = document_metadata.get(
                            "file_guid"
                        )

                        if file_id and file_guid:

                            tender_key = (
                                tender.get(
                                    "tenderNumber"
                                )
                                or tender.get(
                                    "publishedDocumentID"
                                )
                            )

                            print(
                                "[Sindh PPRA] "
                                "Downloading bidding document..."
                            )

                            download_result = (
                                download_sindh_document(
                                    file_id=file_id,
                                    file_guid=file_guid,
                                    tender_key=tender_key,
                                    document_name=(
                                        "Bidding Document.pdf"
                                    ),
                                )
                            )

                            documents.append(
                                {
                                    "document_type": "PRIMARY",
                                    "document_name": (
                                        "Bidding Document.pdf"
                                    ),
                                    "source_url": None,
                                    **download_result,
                                }
                            )

                            # Store metadata-derived
                            # information in the raw record.
                            mapped_tender[
                                "primary_document_url"
                            ] = None

                            print(
                                "[Sindh PPRA] "
                                "Document downloaded."
                            )

                        else:

                            print(
                                "[Sindh PPRA] "
                                "Document metadata missing "
                                "file ID/GUID."
                            )

                    else:

                        print(
                            "[Sindh PPRA] "
                            "No document metadata found."
                        )

                except Exception as exc:

                    print(
                        "[Sindh PPRA] Document download "
                        f"failed: {exc}"
                    )

            else:

                print(
                    "[Sindh PPRA] No "
                    "publishedDocumentID."
                )

            # -----------------------------------------------
            # Persist ALL tenders
            # -----------------------------------------------

            persist_tender(
                db,
                mapped_tender=mapped_tender,
                relevance=relevance,
            )

            processed += 1

            print(
                f"[Sindh PPRA] Persisted tender "
                f"{index}/{len(tenders)}"
            )

        # ----------------------------------------------------
        # 4. Summary
        # ----------------------------------------------------

        print()
        print("-" * 70)
        print("SINDH PPRA SUMMARY")
        print("-" * 70)

        print(
            f"Total scraped:     {len(tenders)}"
        )

        print(
            f"Processed/stored:  {processed}"
        )

        print(
            f"Relevant:          {relevant_count}"
        )

        print(
            f"Irrelevant:        "
            f"{len(tenders) - relevant_count}"
        )

        # ----------------------------------------------------
        # 5. Update checkpoint
        # ----------------------------------------------------
        #
        # Only update after ALL tenders have been
        # successfully persisted.
        #

        checkpoint_updated = (
            update_checkpoint_from_result(
                portal=SINDH_PORTAL,
                result=result,
            )
        )

        print()
        print(
            f"[Sindh PPRA] Checkpoint updated: "
            f"{checkpoint_updated}"
        )

        return {
            "success": True,
            "scraped": len(tenders),
            "processed": processed,
            "relevant": relevant_count,
            "checkpoint_updated": checkpoint_updated,
        }

    except Exception:

        db.rollback()

        print()
        print(
            "[Sindh PPRA] Processing failed. "
            "Checkpoint was NOT updated."
        )

        raise

    finally:

        db.close()
# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "TENDER INTELLIGENCE PIPELINE"
    )

    print(
        "=" * 70
    )

    print()
    print(
        "Phase 1"
    )

    print(
        "Sources: Federal PPRA + Punjab PPRA + Balochistan PPRA + KP PPRA"
    )

    print(
        f"Run date: {TODAY}"
    )

    print(
        "Processing: Scrape -> Relevance -> "
        "Normalize -> Persistent Storage -> Checkpoint"
    )

    print(
        "=" * 70
    )

    results = {}

    # --------------------------------------------------------
    # Federal
    # --------------------------------------------------------

    try:

        results[
            FEDERAL_PORTAL
        ] = process_federal()

    except Exception as error:

        print()
        print("=" * 70)
        print("[Federal PPRA] PIPELINE FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        results[
            FEDERAL_PORTAL
        ] = {
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # Punjab
    # --------------------------------------------------------

    try:

        results[
            PUNJAB_PORTAL
        ] = process_punjab()

    except Exception as error:

        print()
        print("=" * 70)
        print("[Punjab PPRA] PIPELINE FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        results[
            PUNJAB_PORTAL
        ] = {
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # Balochistan
    # --------------------------------------------------------

    try:

        results[
            BALOCHISTAN_PORTAL
        ] = process_balochistan()

    except Exception as error:

        print()
        print("=" * 70)
        print("[Balochistan PPRA] PIPELINE FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        results[
            BALOCHISTAN_PORTAL
        ] = {
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # KP
    # --------------------------------------------------------

    try:

        results[
            KP_PORTAL
        ] = process_kp()

    except Exception as error:

        print()
        print("=" * 70)
        print("[KP PPRA] PIPELINE FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        results[
            KP_PORTAL
        ] = {
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # Sindh
    # --------------------------------------------------------

    try:

        results[
            SINDH_PORTAL
        ] = process_sindh()

    except Exception as error:

        print()
        print("=" * 70)
        print("[Sindh PPRA] PIPELINE FAILED")
        print("=" * 70)

        print(
            f"Error: {error}"
        )

        results[
            SINDH_PORTAL
        ] = {
            "success": False,
            "error": str(error),
        }

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print()

    print("=" * 70)

    print(
        "PIPELINE SUMMARY"
    )

    print(
        "=" * 70
    )

    for portal, result in results.items():

        print()
        print(
            portal
        )

        print(
            "-" * 70
        )

        if result.get(
            "success",
            False,
        ):

            print(
                f"Scraped:  "
                f"{result.get('scraped', 0)}"
            )

            print(
                f"Kept:     "
                f"{result.get('kept', 0)}"
            )

            print(
                f"Checkpoint updated: "
                f"{result.get('checkpoint_updated', False)}"
            )

        else:

            print(
                "FAILED"
            )

            print(
                f"Error: "
                f"{result.get('error', 'Unknown error')}"
            )

    print()
    print(
        "=" * 70
    )

    print(
        "PIPELINE COMPLETE"
    )

    print(
        "=" * 70
    )

    return results


if __name__ == "__main__":
    main()