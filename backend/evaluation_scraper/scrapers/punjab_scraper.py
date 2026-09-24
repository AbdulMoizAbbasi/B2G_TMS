import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from curl_cffi import requests
from bs4 import BeautifulSoup


BASE_URL = "https://eproc.punjab.gov.pk"

EVALUATION_URL = f"{BASE_URL}/Tender_Evaluation_Report.aspx"

PDF_STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation_pdfs"
)


def create_session():
    session = requests.Session(
        impersonate="chrome"
    )

    return session


def clean_text(value):
    if value is None:
        return None

    return " ".join(value.split()).strip()


def get_hidden_fields(soup):
    """
    Extract ASP.NET hidden fields required for the POST request.
    """

    fields = {}

    for input_tag in soup.select("input[type='hidden']"):
        name = input_tag.get("name")

        if not name:
            continue

        fields[name] = input_tag.get("value", "")

    return fields


def extract_evaluation_rows(soup):
    """
    Extract evaluation records from the Telerik RadGrid.
    """

    rows = []

    # Find the table containing the evaluation grid.
    tables = soup.find_all("table")

    for table in tables:

        headers = [
            clean_text(
                th.get_text(" ", strip=True)
            )
            for th in table.find_all("th")
        ]

        if not headers:
            continue

        required_headers = {
            "Department",
            "Procurement Name",
            "Publish Date",
            "Close Date",
            "First Lowest Firm Name",
            "Downlaod",
        }

        if not required_headers.issubset(
            set(headers)
        ):
            continue

        # We found the correct RadGrid.
        for tr in table.find_all("tr"):

            cells = tr.find_all("td")

            if len(cells) < 6:
                continue

            # -------------------------------------------------
            # Skip Telerik header/filter row
            # -------------------------------------------------

            row_text = clean_text(
                tr.get_text(" ", strip=True)
            )

            if (
                "Department" in row_text
                and "Procurement Name" in row_text
                and "Publish Date" in row_text
            ):
                continue

            # -------------------------------------------------
            # Extract evaluation fields
            # -------------------------------------------------

            department = clean_text(
                cells[0].get_text(
                    " ",
                    strip=True,
                )
            )

            procurement_name = clean_text(
                cells[1].get_text(
                    " ",
                    strip=True,
                )
            )

            publish_date = clean_text(
                cells[2].get_text(
                    " ",
                    strip=True,
                )
            )

            close_date = clean_text(
                cells[3].get_text(
                    " ",
                    strip=True,
                )
            )

            awarded_firm = clean_text(
                cells[4].get_text(
                    " ",
                    strip=True,
                )
            )

            # -------------------------------------------------
            # Download cell
            # -------------------------------------------------

            download_link = cells[5].find("a")

            pdf_url = None

            if download_link:

                href = download_link.get("href")

                if href:
                    pdf_url = urljoin(
                        BASE_URL,
                        href,
                    )

            # Ignore empty/grid formatting rows.
            if not procurement_name:
                continue

            rows.append(
                {
                    "department": department,
                    "procurement_name": procurement_name,
                    "publish_date": publish_date,
                    "close_date": close_date,
                    "awarded_firm": awarded_firm,
                    "pdf_url": pdf_url,
                }
            )

        break

    return rows


def download_pdf(
    pdf_url,
    tender_no,
):
    """
    Download evaluation PDF.

    This function is kept separate from get_evaluations()
    so the orchestrator can decide when the PDF actually
    needs to be downloaded.
    """

    if not pdf_url:
        return None

    session = create_session()

    safe_tender_name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        str(tender_no),
    ).strip()

    tender_dir = (
        PDF_STORAGE_DIR
        / safe_tender_name
    )

    tender_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    response = session.get(
        pdf_url,
        timeout=60,
        allow_redirects=True,
    )

    response.raise_for_status()

    content = response.content

    # Basic PDF validation.
    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if (
        not content.startswith(b"%PDF")
        and "pdf" not in content_type
    ):
        raise ValueError(
            f"Downloaded content is not a PDF. "
            f"Content-Type: {content_type}"
        )

    # Try to get a useful filename.
    filename = None

    content_disposition = (
        response.headers.get(
            "Content-Disposition",
            "",
        )
    )

    match = re.search(
        r'filename="?([^"]+)"?',
        content_disposition,
        re.IGNORECASE,
    )

    if match:
        filename = match.group(1)

    if not filename:
        filename = Path(
            urlparse(pdf_url).path
        ).name

    if not filename:
        filename = "evaluation.pdf"

    # Remove unsafe characters.
    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename,
    )

    pdf_path = (
        tender_dir
        / filename
    )

    pdf_path.write_bytes(content)

    print(
        f"PDF saved: {pdf_path}"
    )

    # Return path relative to evaluation_pdfs/
    relative_pdf_path = pdf_path.relative_to(
        PDF_STORAGE_DIR
    )

    return str(relative_pdf_path)


def get_evaluations(tender_name):
    """
    Search Punjab PPRA Evaluation Reports
    by Procurement Name.

    This reproduces the ASP.NET Web Forms +
    Telerik RadGrid filtering mechanism.

    IMPORTANT:
    This function only searches and returns
    matching evaluation metadata.

    PDF downloading is handled separately by
    the orchestrator.
    """

    session = create_session()

    print("\n" + "=" * 70)
    print("PUNJAB PPRA EVALUATION SEARCH")
    print("=" * 70)

    print(
        f"Tender Name: {tender_name}"
    )

    # ---------------------------------------------------------
    # STEP 1: Initial GET
    # ---------------------------------------------------------

    print(
        "\n[1] Loading evaluation page..."
    )

    response = session.get(
        EVALUATION_URL,
        timeout=60,
    )

    response.raise_for_status()

    print(
        f"Status Code: {response.status_code}"
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # ---------------------------------------------------------
    # STEP 2: Extract ASP.NET state
    # ---------------------------------------------------------

    hidden_fields = get_hidden_fields(
        soup
    )

    print(
        f"Hidden fields found: "
        f"{len(hidden_fields)}"
    )

    # ---------------------------------------------------------
    # STEP 3: Build Telerik filter POST
    # ---------------------------------------------------------

    event_target = (
        "ctl00$ContentPlaceHolderSRIS$RadGrid1"
    )

    event_argument = (
        "FireCommand:"
        "ctl00$ContentPlaceHolderSRIS$RadGrid1$ctl00;"
        "Filter;"
        f"Tender_Name|{tender_name}|Contains"
    )

    payload = hidden_fields.copy()

    payload.update(
        {
            "__EVENTTARGET": event_target,

            "__EVENTARGUMENT": event_argument,

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl02$ctl02$"
                "FilterTextBox_Deptt_Name"
            ): "",

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl02$ctl02$"
                "FilterTextBox_Tender_Name"
            ): tender_name,

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl02$ctl02$"
                "FilterTextBox_Publish_Date"
            ): "",

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl02$ctl02$"
                "FilterTextBox_Contract_Award_Date"
            ): "",

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl02$ctl02$"
                "FilterTextBox_Awarded_Firm_Name"
            ): "",

            (
                "ctl00$ContentPlaceHolderSRIS$RadGrid1$"
                "ctl00$ctl03$ctl01$"
                "PageSizeComboBox"
            ): "100",
        }
    )

    print(
        "\n[2] Sending Telerik filter POST..."
    )

    post_response = session.post(
        EVALUATION_URL,
        data=payload,
        timeout=60,
    )

    post_response.raise_for_status()

    print(
        f"POST Status Code: "
        f"{post_response.status_code}"
    )

    # ---------------------------------------------------------
    # STEP 4: Parse filtered response
    # ---------------------------------------------------------

    result_soup = BeautifulSoup(
        post_response.text,
        "html.parser",
    )

    evaluations = extract_evaluation_rows(
        result_soup
    )

    # ---------------------------------------------------------
    # Keep only evaluations that actually belong to
    # the requested procurement name.
    # ---------------------------------------------------------

    requested_name = clean_text(
        tender_name
    )

    matched_evaluations = []

    for evaluation in evaluations:

        returned_name = clean_text(
            evaluation.get(
                "procurement_name"
            )
        )

        if returned_name == requested_name:

            matched_evaluations.append(
                evaluation
            )

    evaluations = matched_evaluations

    print(
        f"\nMatching evaluations found: "
        f"{len(evaluations)}"
    )

    # ---------------------------------------------------------
    # STEP 5: Display matched evaluations
    # ---------------------------------------------------------

    for index, evaluation in enumerate(
        evaluations,
        start=1,
    ):

        print(
            f"\nEvaluation #{index}"
        )

        print(
            f"Department: "
            f"{evaluation['department']}"
        )

        print(
            f"Procurement Name: "
            f"{evaluation['procurement_name']}"
        )

        print(
            f"Publish Date: "
            f"{evaluation['publish_date']}"
        )

        print(
            f"Close Date: "
            f"{evaluation['close_date']}"
        )

        print(
            f"First Lowest Firm: "
            f"{evaluation['awarded_firm']}"
        )

        print(
            f"PDF URL: "
            f"{evaluation['pdf_url']}"
        )

    # ---------------------------------------------------------
    # IMPORTANT:
    # Do NOT download PDFs here.
    #
    # The orchestrator will:
    #   1. Generate evaluation ID
    #   2. Check whether it already exists
    #   3. Download PDF only if it is new
    #   4. Run OCR
    #   5. Save evaluation
    # ---------------------------------------------------------

    return evaluations


if __name__ == "__main__":

    test_tender = (
        "Hiring of External Audit Firm 2026-2027"
    )

    results = get_evaluations(
        test_tender
    )

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)