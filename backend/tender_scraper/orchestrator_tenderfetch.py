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
            "kept": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    relevant = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        keyword_score = relevance.get(
            "keyword_score",
            0,
        )

        #
        # Only tenders with at least one
        # relevant keyword are kept.
        #
        if keyword_score <= 0:
            continue

        normalized = normalize_tender(
            tender=tender,
            portal=FEDERAL_PORTAL,
            relevance=relevance,
        )

        relevant.append(
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
        f"Kept:       {len(relevant)}"
    )

    print(
        f"Discarded:  "
        f"{len(tenders) - len(relevant)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    storage_result = upsert_relevant_tenders(
        relevant
    )

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

    for tender in relevant[:10]:

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
        "kept": len(relevant),
        "storage": storage_result,
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
            "kept": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    relevant = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        keyword_score = relevance.get(
            "keyword_score",
            0,
        )

        #
        # Score 0 = irrelevant.
        #
        if keyword_score <= 0:
            continue

        normalized = normalize_tender(
            tender=tender,
            portal=PUNJAB_PORTAL,
            relevance=relevance,
        )

        relevant.append(
            normalized
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("PUNJAB RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Kept:       {len(relevant)}"
    )

    print(
        f"Discarded:  "
        f"{len(tenders) - len(relevant)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    storage_result = upsert_relevant_tenders(
        relevant
    )

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
    # 6. Show relevant tenders
    # --------------------------------------------------------

    print()
    print(
        "PUNJAB PPRA - TOP RELEVANT TENDERS"
    )

    print("=" * 70)

    for tender in relevant[:10]:

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

        print("Tender Notice URL:")
        print(
            tender.get(
                "tender_notice_url",
                "",
            )
            or "N/A"
        )

        print("-" * 70)

    return {
        "success": True,
        "scraped": len(tenders),
        "kept": len(relevant),
        "storage": storage_result,
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
            "kept": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    relevant = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        keyword_score = relevance.get(
            "keyword_score",
            0,
        )

        #
        # Score 0 = irrelevant.
        #
        if keyword_score <= 0:
            continue

        normalized = normalize_tender(
            tender=tender,
            portal=BALOCHISTAN_PORTAL,
            relevance=relevance,
        )

        relevant.append(
            normalized
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("BALOCHISTAN RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Kept:       {len(relevant)}"
    )

    print(
        f"Discarded:  "
        f"{len(tenders) - len(relevant)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    storage_result = upsert_relevant_tenders(
        relevant
    )

    # --------------------------------------------------------
    # 5. Update checkpoint
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=BALOCHISTAN_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show relevant tenders
    # --------------------------------------------------------

    print()
    print(
        "BALOCHISTAN PPRA - TOP RELEVANT TENDERS"
    )

    print("=" * 70)

    for tender in relevant[:10]:

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

        print("TSE Number:")
        print(
            tender.get(
                "TSENumber",
                "",
            )
            or "N/A"
        )

        print("Title:")
        print(
            tender.get(
                "Name",
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

        print("Tender Notice:")
        print(
            tender.get(
                "tenderNoticeDoc",
                "",
            )
            or "N/A"
        )

        print("-" * 70)

    return {
        "success": True,
        "scraped": len(tenders),
        "kept": len(relevant),
        "storage": storage_result,
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
            "kept": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    relevant = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        keyword_score = relevance.get(
            "keyword_score",
            0,
        )

        #
        # Score 0 = irrelevant.
        #
        if keyword_score <= 0:
            continue

        normalized = normalize_tender(
            tender=tender,
            portal=KP_PORTAL,
            relevance=relevance,
        )

        relevant.append(
            normalized
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("KP RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Kept:       {len(relevant)}"
    )

    print(
        f"Discarded:  "
        f"{len(tenders) - len(relevant)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    storage_result = upsert_relevant_tenders(
        relevant
    )

    # --------------------------------------------------------
    # 5. Update checkpoint
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=KP_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show relevant tenders
    # --------------------------------------------------------

    print()
    print(
        "KP PPRA - TOP RELEVANT TENDERS"
    )

    print("=" * 70)

    for tender in relevant[:10]:

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
        "kept": len(relevant),
        "storage": storage_result,
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
            "kept": 0,
            "checkpoint_updated": False,
        }

    # --------------------------------------------------------
    # 2. Relevance analysis
    # --------------------------------------------------------

    relevant = []

    for tender in tenders:

        analysis = analyze_tender(
            tender
        )

        relevance = analysis[
            "relevance"
        ]

        keyword_score = relevance.get(
            "keyword_score",
            0,
        )

        #
        # Score 0 = irrelevant.
        #
        if keyword_score <= 0:
            continue

        normalized = normalize_tender(
            tender=tender,
            portal=SINDH_PORTAL,
            relevance=relevance,
        )

        relevant.append(
            normalized
        )

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("SINDH RELEVANCE SUMMARY")
    print("-" * 70)

    print(
        f"Total:      {len(tenders)}"
    )

    print(
        f"Kept:       {len(relevant)}"
    )

    print(
        f"Discarded:  "
        f"{len(tenders) - len(relevant)}"
    )

    # --------------------------------------------------------
    # 4. Persistent storage
    # --------------------------------------------------------

    storage_result = upsert_relevant_tenders(
        relevant
    )

    # --------------------------------------------------------
    # 5. Update checkpoint
    # --------------------------------------------------------

    checkpoint_updated = (
        update_checkpoint_from_result(
            portal=SINDH_PORTAL,
            result=result,
        )
    )

    # --------------------------------------------------------
    # 6. Show relevant tenders
    # --------------------------------------------------------

    print()
    print(
        "SINDH PPRA - TOP RELEVANT TENDERS"
    )

    print("=" * 70)

    for tender in relevant[:10]:

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
        "kept": len(relevant),
        "storage": storage_result,
        "checkpoint_updated": checkpoint_updated,
    }

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