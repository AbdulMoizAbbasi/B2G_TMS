import json
from pathlib import Path


from evaluation_scraper.scrapers.federal_scraper import (
    get_evaluations,
)

from evaluation_scraper.scrapers.kp_scraper import (
    get_evaluations as get_kp_evaluations,
)
from evaluation_scraper.scrapers.punjab_scraper import (
    get_evaluations as get_punjab_evaluations,
    download_pdf as download_punjab_pdf,
)

from evaluation_scraper.ocr import (
    process_evaluation_pdf,
)

from evaluation_scraper.storage import (
    save_evaluation,
    get_evaluation,
    get_evaluations_for_tender,
)


# =============================================================
# PATHS
# =============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BACKEND_DIR / "data"

RELEVANT_TENDERS_FILE = (
    DATA_DIR / "relevant_tenders.json"
)


# =============================================================
# SOURCE NAMES
# =============================================================

FEDERAL_PPRA = "Federal PPRA"

PUNJAB_PPRA = "Punjab PPRA"

BALOCHISTAN_PPRA = "Balochistan PPRA"

KP_PPRA = "KP PPRA"


# =============================================================
# LOAD RELEVANT TENDERS
# =============================================================

def load_relevant_tenders():
    """
    Load the currently saved relevant tenders.

    The evaluation system works only with tenders that
    already exist in relevant_tenders.json.
    """

    if not RELEVANT_TENDERS_FILE.exists():

        print(
            f"Relevant tenders file not found: "
            f"{RELEVANT_TENDERS_FILE}"
        )

        return []

    try:

        with open(
            RELEVANT_TENDERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ) as exc:

        print(
            f"Failed to load relevant tenders: {exc}"
        )

        return []

    if not isinstance(data, list):

        print(
            "relevant_tenders.json does not contain "
            "a list."
        )

        return []

    return data


# =============================================================
# GET EVALUATION LOOKUP VALUE
# =============================================================

def get_lookup_value(tender):
    """
    Determine which identifier should be used to
    search for an evaluation based on the tender source.

    Federal:
        web_tender_no

    Balochistan:
        TSENumber

    Punjab:
        tender_number if available,
        otherwise tender_details.

    KP:
        tender_number.
    """

    source = tender.get(
        "source"
    )

    # ---------------------------------------------------------
    # FEDERAL PPRA
    # ---------------------------------------------------------

    if source == FEDERAL_PPRA:

        return tender.get(
            "web_tender_no"
        )

    # ---------------------------------------------------------
    # BALOCHISTAN PPRA
    # ---------------------------------------------------------

    if source == BALOCHISTAN_PPRA:

        return tender.get(
            "TSENumber"
        )

    # ---------------------------------------------------------
    # PUNJAB PPRA
    # ---------------------------------------------------------

    if source == PUNJAB_PPRA:

        tender_number = tender.get(
            "tender_number"
        )

        if tender_number:

            return tender_number

        return tender.get(
            "tender_details"
        )

    # ---------------------------------------------------------
    # KP PPRA
    # ---------------------------------------------------------

    if source == KP_PPRA:

        return tender.get(
            "tender_number"
        )

    # ---------------------------------------------------------
    # UNKNOWN SOURCE
    # ---------------------------------------------------------

    return None


# =============================================================
# PROCESS FEDERAL EVALUATIONS
# =============================================================

def process_federal_tender(
    tender
):
    """
    Process evaluation reports for one
    Federal PPRA tender.
    """

    source = FEDERAL_PPRA

    tender_no = tender.get(
        "web_tender_no"
    )

    if not tender_no:

        return {
            "status": "skipped",
            "reason": "Federal tender has no web_tender_no",
        }

    # =========================================================
    # CHECK EXISTING EVALUATIONS
    # =========================================================

    existing_evaluations = (
        get_evaluations_for_tender(
            source=source,
            tender_no=tender_no
        )
    )

    if existing_evaluations:

        print(
            f"\nSKIP: {tender_no}"
        )

        print(
            "Evaluation already exists in storage."
        )

        return {
            "status": "already_processed",
            "source": source,
            "tender_no": tender_no,
            "evaluations": existing_evaluations,
        }

    # =========================================================
    # SEARCH FEDERAL PPRA
    # =========================================================

    print(
        f"\nCHECKING FEDERAL PPRA: "
        f"{tender_no}"
    )

    evaluations = get_evaluations(
        tender_no
    )

    # =========================================================
    # NO EVALUATION FOUND
    # =========================================================

    if not evaluations:

        print(
            f"No evaluation found for "
            f"{tender_no}"
        )

        return {
            "status": "not_found",
            "source": source,
            "tender_no": tender_no,
            "evaluations": [],
        }

    # =========================================================
    # PROCESS EACH EVALUATION
    # =========================================================

    saved_evaluations = []

    for evaluation in evaluations:

        evaluation_id = evaluation.get(
            "evaluation_id"
        )

        print(
            f"\nProcessing evaluation: "
            f"{evaluation_id}"
        )

        # -----------------------------------------------------
        # SCRAPED DATA
        # -----------------------------------------------------

        scraped_data = {
            "source": source,

            "tender_no": tender_no,

            "evaluation_date": (
                evaluation.get(
                    "evaluation_date"
                )
            ),

            "detail_page_data": (
                evaluation.get(
                    "detail_page_data",
                    {}
                )
            ),
        }

        # -----------------------------------------------------
        # OCR DATA
        # -----------------------------------------------------

        ocr_data = {}

        pdf_path = evaluation.get(
            "pdf_path"
        )

        if not pdf_path:

            print(
                "No PDF available. "
                "OCR skipped."
            )

        else:

            pdf_path = Path(
                pdf_path
            )

            if not pdf_path.exists():

                print(
                    f"PDF does not exist: "
                    f"{pdf_path}"
                )

            else:

                try:

                    print(
                        f"Running OCR: "
                        f"{pdf_path}"
                    )

                    ocr_data = (
                        process_evaluation_pdf(
                            pdf_path
                        )
                    )

                    print(
                        "OCR completed."
                    )

                except Exception as exc:

                    print(
                        f"OCR failed: {exc}"
                    )

                    ocr_data = {
                        "error": str(exc)
                    }

        # -----------------------------------------------------
        # FINAL EVALUATION RECORD
        # -----------------------------------------------------

        final_evaluation = {

            "evaluation_id":
                evaluation_id,

            "scraped_data":
                scraped_data,

            "ocr_data":
                ocr_data,

            "detail_url":
                evaluation.get(
                    "detail_url"
                ),

            "pdf_url":
                evaluation.get(
                    "pdf_url"
                ),

            "pdf_path":
                evaluation.get(
                    "pdf_path"
                ),
        }

        # -----------------------------------------------------
        # SAVE
        # -----------------------------------------------------

        saved = save_evaluation(
            final_evaluation
        )

        saved_evaluations.append(
            saved
        )

    return {
        "status": "processed",
        "source": source,
        "tender_no": tender_no,
        "evaluations": saved_evaluations,
    }


# =============================================================
# PROCESS KP EVALUATIONS
# =============================================================

def process_kp_tender(
    tender
):
    """
    Process evaluation reports for one
    KP PPRA tender.

    KP can have:

    1. Main evaluation PDF
    2. Additional uploaded documents such as:
       - Comparative Statement
       - Technical Document
       - Financial Document
       - Final Document

    Every available PDF is OCR processed.
    """

    source = KP_PPRA

    tender_no = tender.get(
        "tender_number"
    )

    if not tender_no:

        return {
            "status": "skipped",
            "reason": "KP tender has no tender_number",
        }

    # =========================================================
    # CHECK EXISTING EVALUATIONS
    # =========================================================

    existing_evaluations = (
        get_evaluations_for_tender(
            source=source,
            tender_no=tender_no
        )
    )

    if existing_evaluations:

        print(
            f"\nSKIP KP: {tender_no}"
        )

        print(
            "Evaluation already exists in storage."
        )

        return {
            "status": "already_processed",
            "source": source,
            "tender_no": tender_no,
            "evaluations": existing_evaluations,
        }

    # =========================================================
    # SEARCH KP PPRA
    # =========================================================

    print(
        f"\nCHECKING KP PPRA: "
        f"{tender_no}"
    )

    evaluations = get_kp_evaluations(
        tender_no
    )

    # =========================================================
    # NO EVALUATION FOUND
    # =========================================================

    if not evaluations:

        print(
            f"No evaluation found for "
            f"KP tender {tender_no}"
        )

        return {
            "status": "not_found",
            "source": source,
            "tender_no": tender_no,
            "evaluations": [],
        }

    # =========================================================
    # PROCESS EACH KP EVALUATION
    # =========================================================

    saved_evaluations = []

    for evaluation in evaluations:

        evaluation_id = evaluation.get(
            "evaluation_id"
        )

        print(
            f"\nProcessing KP evaluation: "
            f"{evaluation_id}"
        )

        # -----------------------------------------------------
        # DETAIL PAGE DATA
        # -----------------------------------------------------

        detail_page_data = evaluation.get(
            "detail_page_data",
            {}
        )

        # -----------------------------------------------------
        # PROCESS MAIN EVALUATION PDF
        # -----------------------------------------------------

        main_ocr_data = {}

        pdf_path = evaluation.get(
            "pdf_path"
        )

        if not pdf_path:

            print(
                "No main evaluation PDF available."
            )

        else:

            pdf_path = Path(
                pdf_path
            )

            if not pdf_path.exists():

                print(
                    f"Main PDF does not exist: "
                    f"{pdf_path}"
                )

            else:

                try:

                    print(
                        f"Running OCR on main KP PDF: "
                        f"{pdf_path}"
                    )

                    main_ocr_data = (
                        process_evaluation_pdf(
                            pdf_path
                        )
                    )

                    print(
                        "Main KP PDF OCR completed."
                    )

                except Exception as exc:

                    print(
                        f"Main KP PDF OCR failed: "
                        f"{exc}"
                    )

                    main_ocr_data = {
                        "error": str(exc)
                    }

        # -----------------------------------------------------
        # PROCESS ADDITIONAL KP DOCUMENTS
        # -----------------------------------------------------

        documents = evaluation.get(
            "documents",
            []
        )

        processed_documents = []

        for document in documents:

            document_copy = dict(
                document
            )

            document_pdf_path = document.get(
                "pdf_path"
            )

            document_ocr_data = {}

            if not document_pdf_path:

                print(
                    f"No PDF available for "
                    f"{document.get('document_type')}"
                )

            else:

                document_pdf_path = Path(
                    document_pdf_path
                )

                if not document_pdf_path.exists():

                    print(
                        f"Document PDF does not exist: "
                        f"{document_pdf_path}"
                    )

                else:

                    try:

                        print(
                            f"Running OCR on KP document: "
                            f"{document_pdf_path}"
                        )

                        document_ocr_data = (
                            process_evaluation_pdf(
                                document_pdf_path
                            )
                        )

                        print(
                            "Document OCR completed."
                        )

                    except Exception as exc:

                        print(
                            f"Document OCR failed: "
                            f"{exc}"
                        )

                        document_ocr_data = {
                            "error": str(exc)
                        }

            document_copy[
                "ocr_data"
            ] = document_ocr_data

            processed_documents.append(
                document_copy
            )

        # -----------------------------------------------------
        # ADD PROCESSED DOCUMENTS TO DETAIL DATA
        # -----------------------------------------------------

        detail_page_data = dict(
            detail_page_data
        )

        detail_page_data[
            "documents"
        ] = processed_documents

        # -----------------------------------------------------
        # SCRAPED DATA
        # -----------------------------------------------------

        scraped_data = {

            "source":
                source,

            "tender_no":
                tender_no,

            "evaluation_date":
                evaluation.get(
                    "evaluation_date"
                ),

            "detail_page_data":
                detail_page_data,
        }

        # -----------------------------------------------------
        # FINAL KP EVALUATION RECORD
        # -----------------------------------------------------

        final_evaluation = {

            "evaluation_id":
                evaluation_id,

            "scraped_data":
                scraped_data,

            "ocr_data":
                main_ocr_data,

            "detail_url":
                evaluation.get(
                    "detail_url"
                ),

            "pdf_url":
                evaluation.get(
                    "pdf_url"
                ),

            "pdf_path":
                evaluation.get(
                    "pdf_path"
                ),
        }

        # -----------------------------------------------------
        # SAVE
        # -----------------------------------------------------

        saved = save_evaluation(
            final_evaluation
        )

        saved_evaluations.append(
            saved
        )

    return {
        "status": "processed",
        "source": source,
        "tender_no": tender_no,
        "evaluations": saved_evaluations,
    }


# =============================================================
# PROCESS PUNJAB EVALUATIONS
# =============================================================

def process_punjab_tender(tender):
    """
    Process one Punjab PPRA tender.

    Flow:
        1. Search Punjab evaluation reports.
        2. Generate deterministic evaluation ID from PDF URL.
        3. Check JSON storage BEFORE downloading PDF.
        4. If already stored, skip completely.
        5. If new, download PDF.
        6. Run OCR.
        7. Save evaluation.
    """

    source = PUNJAB_PPRA

    tender_no = tender.get("tender_number")
    tender_name = tender.get("tender_details")

    if not tender_name:
        return {
            "status": "invalid",
            "source": source,
            "tender_no": tender_no,
            "message": "Punjab tender has no tender_details.",
        }

    print("\n" + "=" * 70)
    print("PROCESSING PUNJAB TENDER")
    print("=" * 70)

    print(f"Tender Number: {tender_no}")
    print(f"Tender Name: {tender_name}")

    # ---------------------------------------------------------
    # STEP 1: Tender-level duplicate check
    # ---------------------------------------------------------

    if tender_no:
        existing_tender_evaluations = get_evaluations_for_tender(
            source,
            tender_no,
        )

        if existing_tender_evaluations:
            print(
                f"\nEvaluation already exists for "
                f"Punjab tender: {tender_no}"
            )

            return {
                "status": "already_processed",
                "source": source,
                "tender_no": tender_no,
                "evaluations": existing_tender_evaluations,
            }

    # ---------------------------------------------------------
    # STEP 2: Search Punjab evaluation reports
    # ---------------------------------------------------------

    print("\nSearching Punjab evaluation reports...")

    evaluations = get_punjab_evaluations(
        tender_name
    )

    if not evaluations:
        print(
            "\nNo matching Punjab evaluation found."
        )

        return {
            "status": "not_found",
            "source": source,
            "tender_no": tender_no,
            "tender_name": tender_name,
            "evaluations": [],
        }

    print(
        f"\nFound {len(evaluations)} matching "
        f"Punjab evaluation(s)."
    )

    processed_evaluations = []

    # ---------------------------------------------------------
    # STEP 3: Process each evaluation
    # ---------------------------------------------------------

    for evaluation in evaluations:

        pdf_url = evaluation.get("pdf_url")

        if not pdf_url:
            print(
                "\nSkipping evaluation because "
                "PDF URL is missing."
            )
            continue

        # -----------------------------------------------------
        # STEP 4: Generate deterministic evaluation ID
        # -----------------------------------------------------

        import hashlib

        evaluation_id = (
            "punjab_"
            + hashlib.sha256(
                pdf_url.encode("utf-8")
            ).hexdigest()[:16]
        )

        print(
            f"\nEvaluation ID: {evaluation_id}"
        )

        # -----------------------------------------------------
        # STEP 5: CHECK STORAGE BEFORE PDF DOWNLOAD
        # -----------------------------------------------------

        existing_evaluation = get_evaluation(
            evaluation_id
        )

        if existing_evaluation:
            print(
                "\nEvaluation already exists."
            )

            print(
                "Skipping PDF download and OCR."
            )

            processed_evaluations.append(
                existing_evaluation
            )

            continue

        # -----------------------------------------------------
        # STEP 6: Download PDF ONLY for new evaluation
        # -----------------------------------------------------

        print(
            "\nNew evaluation detected."
        )

        print(
            "Downloading evaluation PDF..."
        )

        pdf_path = download_punjab_pdf(
            pdf_url=pdf_url,
            tender_no=tender_name,
        )

        # -----------------------------------------------------
        # STEP 7: Validate PDF path
        # -----------------------------------------------------

        if not pdf_path:
            print(
                "PDF download failed."
            )
            continue

        print(
            f"PDF downloaded: {pdf_path}"
        )

        # -----------------------------------------------------
        # STEP 8: Build absolute PDF path
        # -----------------------------------------------------

        pdf_full_path = (
            DATA_DIR
            / "evaluation_pdfs"
            / pdf_path
        )

        if not pdf_full_path.exists():
            print(
                f"PDF file not found: "
                f"{pdf_full_path}"
            )
            continue

        # -----------------------------------------------------
        # STEP 9: OCR
        # -----------------------------------------------------

        print(
            "\nProcessing Punjab evaluation:"
            f" {evaluation_id}"
        )

        print(
            "Running OCR..."
        )

        ocr_data = process_evaluation_pdf(
            str(pdf_full_path)
        )

        # -----------------------------------------------------
        # STEP 10: Build scraped data
        # -----------------------------------------------------

        scraped_data = {
            "source": source,
            "tender_no": tender_no,
            "evaluation_date": evaluation.get(
                "publish_date"
            ),
            "detail_page_data": {
                "department": evaluation.get(
                    "department"
                ),
                "procurement_name": evaluation.get(
                    "procurement_name"
                ),
                "publish_date": evaluation.get(
                    "publish_date"
                ),
                "close_date": evaluation.get(
                    "close_date"
                ),
                "awarded_firm": evaluation.get(
                    "awarded_firm"
                ),
            },
        }

        # -----------------------------------------------------
        # STEP 11: Create final evaluation record
        # -----------------------------------------------------

        evaluation_record = {
            "evaluation_id": evaluation_id,
            "scraped_data": scraped_data,
            "ocr_data": ocr_data,
            "detail_url": None,
            "pdf_url": pdf_url,
            "pdf_path": pdf_path,
        }

        # -----------------------------------------------------
        # STEP 12: Save
        # -----------------------------------------------------

        saved = save_evaluation(
            evaluation_record
        )

        if saved:
            print(
                "\nPunjab evaluation saved successfully."
            )

            processed_evaluations.append(
                evaluation_record
            )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    if not processed_evaluations:
        return {
            "status": "not_processed",
            "source": source,
            "tender_no": tender_no,
            "tender_name": tender_name,
            "evaluations": [],
        }

    return {
        "status": "processed",
        "source": source,
        "tender_no": tender_no,
        "tender_name": tender_name,
        "evaluations": processed_evaluations,
    }


# =============================================================
# PROCESS ONE TENDER BASED ON SOURCE
# =============================================================

def process_tender(
    tender
):
    """
    Route a tender to the appropriate evaluation
    scraper based on its source.
    """

    source = tender.get(
        "source"
    )

    tender_id = tender.get(
        "id"
    )

    print("\n" + "-" * 70)

    print(
        f"Tender ID: {tender_id}"
    )

    print(
        f"Source: {source}"
    )

    lookup_value = get_lookup_value(
        tender
    )

    print(
        f"Evaluation Lookup: "
        f"{lookup_value}"
    )

    # =========================================================
    # FEDERAL
    # =========================================================

    if source == FEDERAL_PPRA:

        return process_federal_tender(
            tender
        )

    # =========================================================
    # KP
    # =========================================================

    if source == KP_PPRA:

        return process_kp_tender(
            tender
        )

    # =========================================================
    # PUNJAB
    # =========================================================

    if source == PUNJAB_PPRA:

        return process_punjab_tender(
            tender
        )

    # =========================================================
    # BALOCHISTAN
    # =========================================================

    if source == BALOCHISTAN_PPRA:

        print(
            "Balochistan PPRA evaluation scraper "
            "is not implemented yet."
        )

        return {
            "status": "source_not_implemented",
            "source": source,
            "lookup_value": lookup_value,
        }

    # =========================================================
    # UNKNOWN SOURCE
    # =========================================================

    print(
        f"Unknown evaluation source: "
        f"{source}"
    )

    return {
        "status": "unknown_source",
        "source": source,
        "lookup_value": lookup_value,
    }


# =============================================================
# PROCESS ALL RELEVANT TENDERS
# =============================================================

def process_all_relevant_tenders():
    """
    Check evaluation reports for all currently saved
    relevant tenders.

    Only tenders from relevant_tenders.json are processed.
    """

    print("\n" + "=" * 70)

    print(
        "EVALUATION REPORT ORCHESTRATOR"
    )

    print("=" * 70)

    # =========================================================
    # LOAD TENDERS
    # =========================================================

    tenders = load_relevant_tenders()

    print(
        f"Relevant tenders loaded: "
        f"{len(tenders)}"
    )

    if not tenders:

        print(
            "No relevant tenders available."
        )

        return []

    # =========================================================
    # PROCESS
    # =========================================================

    results = []

    for index, tender in enumerate(
        tenders,
        start=1
    ):

        print(
            f"\n\nProcessing tender "
            f"{index}/{len(tenders)}"
        )

        result = process_tender(
            tender
        )

        results.append(
            result
        )

    # =========================================================
    # SUMMARY
    # =========================================================

    processed = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "processed"
    )

    already_processed = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "already_processed"
    )

    not_found = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "not_found"
    )

    not_implemented = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "source_not_implemented"
    )

    print("\n" + "=" * 70)

    print(
        "EVALUATION PROCESS SUMMARY"
    )

    print("=" * 70)

    print(
        f"Total Relevant Tenders: "
        f"{len(tenders)}"
    )

    print(
        f"New Evaluations Processed: "
        f"{processed}"
    )

    print(
        f"Already Processed / Skipped: "
        f"{already_processed}"
    )

    print(
        f"No Evaluation Found: "
        f"{not_found}"
    )

    print(
        f"Source Not Implemented: "
        f"{not_implemented}"
    )

    print("=" * 70)

    return results


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    results = process_all_relevant_tenders()

    print("\nFINAL RESULTS:")

    for result in results:

        print(result)