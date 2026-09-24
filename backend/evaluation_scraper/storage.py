import json
import os
from pathlib import Path


# =============================================================
# DIRECTORIES
# =============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BACKEND_DIR / "data"


# =============================================================
# STORAGE CONFIGURATION
# =============================================================

STORAGE_FILE = Path(
    os.getenv(
        "EVALUATION_STORAGE_FILE",
        str(DATA_DIR / "evaluation_reports.json")
    )
)


PDF_STORAGE_DIR = Path(
    os.getenv(
        "EVALUATION_PDF_DIR",
        str(DATA_DIR / "evaluation_pdfs")
    )
)


# =============================================================
# LOAD ALL EVALUATION REPORTS
# =============================================================

def load_evaluation_reports():
    """
    Load all stored evaluation reports.

    Returns:
        list: Stored evaluation reports.
    """

    if not STORAGE_FILE.exists():
        return []

    try:

        with open(
            STORAGE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


# =============================================================
# SAVE ALL EVALUATION REPORTS
# =============================================================

def save_evaluation_reports(reports):
    """
    Save all evaluation reports to JSON.
    """

    STORAGE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        STORAGE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            reports,
            file,
            indent=4,
            ensure_ascii=False
        )


# =============================================================
# NORMALIZE PDF PATH
# =============================================================

def normalize_pdf_path(pdf_path):
    """
    Convert an absolute PDF filesystem path into
    a path relative to the evaluation PDF storage directory.

    Example:

        C:/project/backend/data/evaluation_pdfs/
        TS0000012466E/EVL00000003147.pdf

    becomes:

        TS0000012466E/EVL00000003147.pdf
    """

    if not pdf_path:
        return None

    path = Path(pdf_path)

    # ---------------------------------------------------------
    # Already relative
    # ---------------------------------------------------------

    if not path.is_absolute():

        return path.as_posix()

    # ---------------------------------------------------------
    # Convert absolute path to path relative to PDF storage
    # ---------------------------------------------------------

    try:

        relative_path = path.resolve().relative_to(
            PDF_STORAGE_DIR.resolve()
        )

        return relative_path.as_posix()

    except ValueError:

        # If the path is outside the configured PDF directory,
        # preserve it rather than silently changing it.
        return path.as_posix()


# =============================================================
# SAVE / UPDATE ONE EVALUATION
# =============================================================

def save_evaluation(evaluation):
    """
    Save or update one evaluation report.

    Evaluations are uniquely identified by evaluation_id.

    The PDF path is normalized before saving so that
    machine-specific absolute paths are not stored in JSON.
    """

    reports = load_evaluation_reports()

    evaluation_id = evaluation.get(
        "evaluation_id"
    )

    if not evaluation_id:

        raise ValueError(
            "evaluation_id is required"
        )

    # ---------------------------------------------------------
    # Work on a copy
    # ---------------------------------------------------------

    evaluation = dict(evaluation)

    # ---------------------------------------------------------
    # Normalize PDF path
    # ---------------------------------------------------------

    if "pdf_path" in evaluation:

        evaluation["pdf_path"] = (
            normalize_pdf_path(
                evaluation.get("pdf_path")
            )
        )

    # ---------------------------------------------------------
    # Update existing evaluation
    # ---------------------------------------------------------

    updated = False

    for index, existing in enumerate(
        reports
    ):

        if existing.get(
            "evaluation_id"
        ) == evaluation_id:

            reports[index] = evaluation

            updated = True

            break

    # ---------------------------------------------------------
    # Add new evaluation
    # ---------------------------------------------------------

    if not updated:

        reports.append(
            evaluation
        )

    save_evaluation_reports(
        reports
    )

    return evaluation


# =============================================================
# GET ONE EVALUATION
# =============================================================

def get_evaluation(evaluation_id):
    """
    Get one evaluation by evaluation ID.

    Returns:
        dict | None
    """

    reports = load_evaluation_reports()

    for evaluation in reports:

        if evaluation.get(
            "evaluation_id"
        ) == evaluation_id:

            return evaluation

    return None


# =============================================================
# GET EVALUATIONS FOR A TENDER
# =============================================================

def get_evaluations_for_tender(
    source,
    tender_no
):
    """
    Get all evaluations already stored for
    a specific source and tender number.

    This is used by the evaluation orchestrator
    before making a new PPRA request.

    Example:

        source = "Federal PPRA"
        tender_no = "TS0000012466E"

    Returns:
        list
    """

    reports = load_evaluation_reports()

    matching = []

    for evaluation in reports:

        scraped_data = evaluation.get(
            "scraped_data",
            {}
        )

        stored_source = scraped_data.get(
            "source"
        )

        stored_tender_no = scraped_data.get(
            "tender_no"
        )

        if (
            stored_source == source
            and stored_tender_no == tender_no
        ):

            matching.append(
                evaluation
            )

    return matching


# =============================================================
# CHECK WHETHER TENDER HAS STORED EVALUATION
# =============================================================

def has_evaluation_for_tender(
    source,
    tender_no
):
    """
    Check whether at least one evaluation
    is already stored for a source and tender.

    Returns:
        bool
    """

    evaluations = get_evaluations_for_tender(
        source,
        tender_no
    )

    return len(evaluations) > 0


# =============================================================
# DELETE ONE EVALUATION
# =============================================================

def delete_evaluation(evaluation_id):
    """
    Delete one evaluation from metadata storage.

    This only removes the evaluation metadata
    from JSON.

    It does NOT delete the PDF file.
    """

    reports = load_evaluation_reports()

    filtered = [
        evaluation
        for evaluation in reports
        if evaluation.get(
            "evaluation_id"
        ) != evaluation_id
    ]

    if len(filtered) == len(reports):

        return False

    save_evaluation_reports(
        filtered
    )

    return True