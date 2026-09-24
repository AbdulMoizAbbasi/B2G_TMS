import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://epms.ppra.gov.pk"

EVALUATION_SEARCH_URL = (
    f"{BASE_URL}/public/evaluations"
)

# Store downloaded evaluation PDFs here
PDF_STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation_pdfs"
)


def extract_detail_page_data(soup):
    """
    Extract structured information from the
    Federal PPRA evaluation detail page.

    The page may contain information in tables,
    label/value rows, or other structured elements.

    This function intentionally extracts the data
    generically so we can inspect the actual fields
    before designing the permanent storage schema.
    """

    details = {}

    # =========================================================
    # TABLE DATA
    # =========================================================

    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

            cells = row.find_all(
                ["th", "td"]
            )

            if len(cells) < 2:
                continue

            values = [
                cell.get_text(
                    " ",
                    strip=True
                )
                for cell in cells
            ]

            values = [
                value
                for value in values
                if value
            ]

            if len(values) < 2:
                continue

            # Most PPRA detail rows are expected to
            # follow a label -> value pattern.
            label = values[0]
            value = " | ".join(values[1:])

            if label and value:

                if label not in details:
                    details[label] = value

    # =========================================================
    # LABEL / VALUE ELEMENTS
    # =========================================================

    # Capture common Bootstrap-style form/display
    # structures where a label and value are separate
    # elements.

    for container in soup.find_all(
        ["div", "p", "li"]
    ):

        text = container.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        # Avoid storing huge blocks of page text.
        if len(text) > 300:
            continue

        # Look for "Label: Value"
        if ":" in text:

            label, value = text.split(
                ":",
                1
            )

            label = label.strip()
            value = value.strip()

            if (
                label
                and value
                and len(label) < 100
                and len(value) < 500
            ):

                if label not in details:
                    details[label] = value

    return details


def print_detail_page_data(details):
    """
    Print extracted evaluation detail data
    in a readable format for inspection.
    """

    print("\n" + "=" * 70)
    print("EVALUATION DETAIL PAGE DATA")
    print("=" * 70)

    if not details:

        print(
            "No structured detail fields were found."
        )

        return

    for label, value in details.items():

        print(
            f"{label}: {value}"
        )


def get_evaluations(tender_no):
    """
    Search Federal PPRA for evaluation reports
    using the Web Tender Number.

    For every evaluation found:
    1. Get evaluation detail page.
    2. Extract evaluation date.
    3. Extract evaluation detail information.
    4. Extract Download Evaluation Report PDF URL.
    5. Download the PDF locally.
    """

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    }

    # =========================================================
    # SEARCH EVALUATIONS
    # =========================================================

    response = session.get(
        EVALUATION_SEARCH_URL,
        params={"tender_no": tender_no},
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    print("=" * 70)
    print("FEDERAL PPRA EVALUATION SEARCH")
    print("=" * 70)
    print(f"Tender Number: {tender_no}")
    print("=" * 70)
    print(f"Status Code: {response.status_code}")
    print(f"Search URL: {response.url}")

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    evaluations = []

    # =========================================================
    # FIND EVALUATION DETAIL LINKS
    # =========================================================

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        )

        if (
            "/public/evaluations/"
            "evaluation-details/"
            not in href
        ):
            continue

        detail_url = urljoin(
            BASE_URL,
            href
        )

        # -----------------------------------------------------
        # EXTRACT EVALUATION ID
        # -----------------------------------------------------

        match = re.search(
            r"/evaluation-details/([^/?#]+)",
            detail_url
        )

        if not match:
            continue

        evaluation_id = match.group(1)

        # -----------------------------------------------------
        # EXTRACT EVALUATION DATE
        # -----------------------------------------------------

        evaluation_date = None

        row = link.find_parent("tr")

        if row:

            date_cell = row.find(
                "td",
                attrs={
                    "data-label": "Advertised"
                }
            )

            if date_cell:

                evaluation_date = (
                    date_cell.get_text(
                        " ",
                        strip=True
                    )
                )

        # =====================================================
        # OPEN EVALUATION DETAIL PAGE
        # =====================================================

        detail_page_data = {}

        pdf_url = None

        try:

            detail_response = session.get(
                detail_url,
                headers=headers,
                timeout=30,
            )

            detail_response.raise_for_status()

        except requests.RequestException as exc:

            print(
                f"\nFailed to open evaluation "
                f"{evaluation_id}: {exc}"
            )

        else:

            detail_soup = BeautifulSoup(
                detail_response.text,
                "html.parser"
            )

            # -------------------------------------------------
            # EXTRACT DETAIL PAGE DATA
            # -------------------------------------------------

            detail_page_data = (
                extract_detail_page_data(
                    detail_soup
                )
            )

            print(
                f"\n\nEvaluation ID: "
                f"{evaluation_id}"
            )

            print(
                f"Detail URL: "
                f"{detail_url}"
            )

            print_detail_page_data(
                detail_page_data
            )

            # -------------------------------------------------
            # FIND DOWNLOAD EVALUATION REPORT
            # -------------------------------------------------

            for pdf_link in detail_soup.find_all(
                "a",
                href=True
            ):

                link_text = pdf_link.get_text(
                    " ",
                    strip=True
                )

                if (
                    "Download Evaluation Report"
                    in link_text
                ):

                    pdf_url = urljoin(
                        BASE_URL,
                        pdf_link["href"]
                    )

                    break

        # =====================================================
        # DOWNLOAD PDF
        # =====================================================

        pdf_path = None

        if pdf_url:

            try:

                # Create tender-specific directory
                tender_pdf_dir = (
                    PDF_STORAGE_DIR
                    / tender_no
                )

                tender_pdf_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )

                pdf_path = (
                    tender_pdf_dir
                    / f"{evaluation_id}.pdf"
                )

                print(
                    f"\nDownloading PDF: "
                    f"{evaluation_id}"
                )

                pdf_response = session.get(
                    pdf_url,
                    headers=headers,
                    timeout=60,
                )

                pdf_response.raise_for_status()

                # -------------------------------------------------
                # VERIFY THAT RESPONSE IS ACTUALLY A PDF
                # -------------------------------------------------

                content_type = (
                    pdf_response.headers
                    .get(
                        "Content-Type",
                        ""
                    )
                    .lower()
                )

                first_bytes = (
                    pdf_response.content[:5]
                )

                if (
                    "pdf" not in content_type
                    and first_bytes != b"%PDF-"
                ):

                    print(
                        "ERROR: Downloaded response "
                        "does not appear to be a PDF."
                    )

                    pdf_path = None

                else:

                    with open(
                        pdf_path,
                        "wb"
                    ) as pdf_file:

                        pdf_file.write(
                            pdf_response.content
                        )

                    print(
                        f"PDF saved: {pdf_path}"
                    )

            except requests.RequestException as exc:

                print(
                    f"Failed to download PDF "
                    f"{evaluation_id}: {exc}"
                )

                pdf_path = None

            except OSError as exc:

                print(
                    f"Failed to save PDF "
                    f"{evaluation_id}: {exc}"
                )

                pdf_path = None

        else:

            print(
                f"\nNo PDF link found for "
                f"{evaluation_id}"
            )

        # =====================================================
        # ADD RESULT
        # =====================================================

        evaluations.append(
            {
                "evaluation_id": evaluation_id,
                "evaluation_date": evaluation_date,
                "detail_url": detail_url,
                "detail_page_data": detail_page_data,
                "pdf_url": pdf_url,
                "pdf_path": (
                    str(pdf_path)
                    if pdf_path
                    else None
                ),
            }
        )

    # =========================================================
    # REMOVE DUPLICATES
    # =========================================================

    unique_evaluations = []

    seen = set()

    for evaluation in evaluations:

        evaluation_id = evaluation[
            "evaluation_id"
        ]

        if evaluation_id in seen:
            continue

        seen.add(evaluation_id)

        unique_evaluations.append(
            evaluation
        )

    # =========================================================
    # PRINT RESULTS
    # =========================================================

    print(
        f"\nEvaluation Reports Found: "
        f"{len(unique_evaluations)}"
    )

    for index, evaluation in enumerate(
        unique_evaluations,
        start=1
    ):

        print(
            f"\nEvaluation #{index}"
        )

        print(
            f"Evaluation ID: "
            f"{evaluation['evaluation_id']}"
        )

        print(
            f"Date: "
            f"{evaluation['evaluation_date']}"
        )

        print(
            f"View: "
            f"{evaluation['detail_url']}"
        )

        print(
            f"PDF: "
            f"{evaluation['pdf_url']}"
        )

        print(
            f"Saved PDF: "
            f"{evaluation['pdf_path']}"
        )

    print(
        "\n" + "=" * 70
    )
    print(
        "END FEDERAL PPRA SEARCH"
    )
    print(
        "=" * 70
    )

    return unique_evaluations


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    tender_number = "TS0000012466E"

    results = get_evaluations(
        tender_number
    )

    print("\nFINAL RESULT:")

    for result in results:

        print(result)