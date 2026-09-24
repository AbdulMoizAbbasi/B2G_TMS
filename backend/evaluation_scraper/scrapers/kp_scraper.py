import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "http://www.kppra.gov.pk/kppra"

EVALUATED_TENDERS_URL = (
    f"{BASE_URL}/evaluated_tenders.php"
)

DOCUMENTS_URL = (
    f"{BASE_URL}/processtender_documents.php"
)

PDF_STORAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation_pdfs"
)


def create_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    })

    return session


def clean_text(value):
    if value is None:
        return None

    value = value.strip()
    value = re.sub(r"\s+", " ", value)

    return value or None


def extract_evaluation_row(soup, tender_no):

    table = soup.find(
        "table",
        class_=lambda value: (
            value and "custom-table" in value
        )
    )

    if not table:
        print("DEBUG: No custom-table found.")
        return None

    # KP may return rows directly under <table>
    # instead of wrapping them inside <tbody>.
    rows = table.find_all("tr")

    print(f"DEBUG: Found {len(rows)} table rows.")

    for row in rows:

        cells = row.find_all("td")

        # Skip header row
        if len(cells) < 6:
            continue

        tender_number = clean_text(
            cells[0].get_text(" ", strip=True)
        )

        print(
            f"DEBUG: Found tender number in row: "
            f"{tender_number}"
        )

        if tender_number != str(tender_no):
            continue

        print(
            f"DEBUG: MATCH FOUND for tender {tender_no}"
        )

        # --------------------------------------------------
        # Tender PDF
        # --------------------------------------------------

        tender_link = cells[0].find(
            "a",
            href=True
        )

        procurement_entity = clean_text(
            cells[1].get_text(" ", strip=True)
        )

        description = clean_text(
            cells[2].get_text(" ", strip=True)
        )

        advertisement_date = clean_text(
            cells[3].get_text(" ", strip=True)
        )

        closing_date = clean_text(
            cells[4].get_text(" ", strip=True)
        )

        pdf_url = None

        if tender_link:

            pdf_href = tender_link.get("href")

            if pdf_href:
                pdf_url = urljoin(
                    BASE_URL + "/",
                    pdf_href
                )

        # --------------------------------------------------
        # Evaluation documents page
        # --------------------------------------------------

        documents_link = cells[5].find(
            "a",
            href=True
        )

        documents_url = None
        tender_id = None

        if documents_link:

            documents_href = documents_link.get(
                "href",
                ""
            )

            documents_url = urljoin(
                BASE_URL + "/",
                documents_href
            )

            match = re.search(
                r"tender_id=([^&#]+)",
                documents_href
            )

            if match:
                tender_id = match.group(1)

        return {
            "tender_no": tender_number,
            "procurement_entity": procurement_entity,
            "description": description,
            "advertisement_date": advertisement_date,
            "closing_date": closing_date,
            "pdf_url": pdf_url,
            "documents_url": documents_url,
            "tender_id": tender_id,
        }

    print(
        f"DEBUG: Tender {tender_no} "
        f"was not found in the table rows."
    )

    return None


def extract_document_information(soup):

    documents = []

    # --------------------------------------------------
    # Find the evaluation information section
    # --------------------------------------------------

    widget = None

    for candidate in soup.find_all(
        ["div", "section"]
    ):

        heading = candidate.find(
            class_="widget_heading"
        )

        if not heading:
            continue

        heading_text = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if heading_text == "Tender Evaluation Information":
            widget = candidate
            break

    if widget is None:
        widget = soup

    # --------------------------------------------------
    # Find all document headings
    # --------------------------------------------------

    document_types = {
        "Comparative Statement",
        "Technical Document",
        "Financial Document",
        "Final Document",
    }

    headings = []

    for heading in widget.find_all("h4"):

        document_type = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if document_type in document_types:
            headings.append(
                (heading, document_type)
            )

    # --------------------------------------------------
    # Process each document section
    # --------------------------------------------------

    for index, (
        heading,
        document_type
    ) in enumerate(headings):

        next_heading = (
            headings[index + 1][0]
            if index + 1 < len(headings)
            else None
        )

        # --------------------------------------------------
        # Collect everything after this heading and
        # before the next document heading.
        # --------------------------------------------------

        section_elements = []

        current = heading

        while True:

            current = current.find_next()

            if current is None:
                break

            # Stop at the next document heading
            if (
                next_heading is not None
                and current == next_heading
            ):
                break

            # Don't leave the evaluation widget
            if (
                widget is not soup
                and current != widget
                and widget not in current.parents
            ):
                break

            section_elements.append(current)

        # --------------------------------------------------
        # Search for PDF download links
        # --------------------------------------------------

        found_document = False

        seen_links = set()

        for element in section_elements:

            if element.name != "a":
                continue

            href = element.get(
                "href",
                ""
            )

            if "force_download.php" not in href:
                continue

            if href in seen_links:
                continue

            seen_links.add(href)

            document_name = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            pdf_url = urljoin(
                BASE_URL + "/",
                href
            )

            # --------------------------------------------------
            # Find upload timestamp
            # --------------------------------------------------

            uploaded_on = None

            # First try the nearest small element
            # around the download link.
            parent = element.parent

            if parent:

                small = parent.find(
                    "small"
                )

                if small:

                    uploaded_text = clean_text(
                        small.get_text(
                            " ",
                            strip=True
                        )
                    )

                    match = re.search(
                        r"\(Uploaded On:\s*(.*?)\)",
                        uploaded_text,
                        flags=re.IGNORECASE
                    )

                    if match:

                        uploaded_on = clean_text(
                            match.group(1)
                        )

            # If not found, search nearby elements
            if uploaded_on is None:

                for nearby in section_elements:

                    if nearby.name != "small":
                        continue

                    uploaded_text = clean_text(
                        nearby.get_text(
                            " ",
                            strip=True
                        )
                    )

                    match = re.search(
                        r"\(Uploaded On:\s*(.*?)\)",
                        uploaded_text,
                        flags=re.IGNORECASE
                    )

                    if match:

                        uploaded_on = clean_text(
                            match.group(1)
                        )

                        break

            documents.append({
                "document_type": document_type,
                "document_name": document_name,
                "uploaded_on": uploaded_on,
                "pdf_url": pdf_url,
            })

            found_document = True

        # --------------------------------------------------
        # No document uploaded
        # --------------------------------------------------

        if not found_document:

            documents.append({
                "document_type": document_type,
                "document_name": None,
                "uploaded_on": None,
                "pdf_url": None,
            })

    return documents


def download_pdf(
    session,
    pdf_url,
    tender_no,
    filename
):

    if not pdf_url:
        return None

    tender_pdf_dir = (
        PDF_STORAGE_DIR / str(tender_no)
    )

    tender_pdf_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    pdf_path = (
        tender_pdf_dir / filename
    )

    try:

        print(
            f"Downloading PDF: {pdf_url}"
        )

        response = session.get(
            pdf_url,
            timeout=60
        )

        response.raise_for_status()

        content_type = (
            response.headers
            .get("Content-Type", "")
            .lower()
        )

        first_bytes = response.content[:5]

        if (
            "pdf" not in content_type
            and first_bytes != b"%PDF-"
        ):

            print(
                "ERROR: Response does not "
                "appear to be a PDF."
            )

            return None

        with open(
            pdf_path,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        print(
            f"PDF saved: {pdf_path}"
        )

        return str(pdf_path)

    except requests.RequestException as exc:

        print(
            f"Failed to download PDF: {exc}"
        )

        return None

    except OSError as exc:

        print(
            f"Failed to save PDF: {exc}"
        )

        return None


def get_evaluations(tender_no):

    session = create_session()

    tender_no = str(
        tender_no
    ).strip()

    if not tender_no:
        return []

    print("\n" + "=" * 70)
    print("KP PPRA EVALUATION SEARCH")
    print("=" * 70)

    print(
        f"Tender Number: {tender_no}"
    )

    # --------------------------------------------------
    # Search evaluated tenders
    # --------------------------------------------------

    try:

        response = session.get(
            EVALUATED_TENDERS_URL,
            params={
                "tender_ref": tender_no,
                "fromDate": "",
                "toDate": "",
                "dpart_id": "",
                "tender_type_id": "",
                "sort_field": "",
                "sort_order": "ASC",
                "search": "Search",
            },
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as exc:

        print(
            f"KP evaluation search failed: {exc}"
        )

        return []

    print(
        f"Status Code: {response.status_code}"
    )

    print(
        f"Search URL: {response.url}"
    )

    # --------------------------------------------------
    # Parse response
    # --------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # --------------------------------------------------
    # DEBUG INFORMATION
    # --------------------------------------------------

    print("\n" + "-" * 70)
    print("KP RESPONSE DEBUG")
    print("-" * 70)

    page_title = (
        soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    print(
        f"PAGE TITLE: {page_title}"
    )

    tables = soup.find_all("table")

    print(
        f"TABLE COUNT: {len(tables)}"
    )

    for index, table in enumerate(
        tables,
        start=1
    ):

        print(
            f"\n--- TABLE {index} ---"
        )

        table_text = table.get_text(
            " ",
            strip=True
        )

        print(
            table_text[:3000]
        )

    print(
        "\n" + "-" * 70
    )

    # --------------------------------------------------
    # Extract evaluation row
    # --------------------------------------------------

    evaluation = extract_evaluation_row(
        soup,
        tender_no
    )

    if not evaluation:

        print(
            f"No evaluation found for "
            f"{tender_no}"
        )

        return []

    # --------------------------------------------------
    # Display evaluation information
    # --------------------------------------------------

    print("\nEvaluation found:")

    print(
        f"Tender No: "
        f"{evaluation['tender_no']}"
    )

    print(
        f"Procurement Entity: "
        f"{evaluation['procurement_entity']}"
    )

    print(
        f"Description: "
        f"{evaluation['description']}"
    )

    print(
        f"Advertisement Date: "
        f"{evaluation['advertisement_date']}"
    )

    print(
        f"Closing Date: "
        f"{evaluation['closing_date']}"
    )

    print(
        f"PDF URL: "
        f"{evaluation['pdf_url']}"
    )

    print(
        f"Documents URL: "
        f"{evaluation['documents_url']}"
    )

    # --------------------------------------------------
    # Download main evaluation PDF
    # --------------------------------------------------

    evaluation_id = (
        evaluation["tender_id"]
        or evaluation["tender_no"]
    )

    main_pdf_path = None

    if evaluation["pdf_url"]:

        main_pdf_path = download_pdf(
            session=session,
            pdf_url=evaluation["pdf_url"],
            tender_no=tender_no,
            filename=(
                f"{tender_no}"
                f"_evaluation.pdf"
            )
        )

    # --------------------------------------------------
    # Open evaluation documents page
    # --------------------------------------------------

    documents = []

    if evaluation["documents_url"]:

        try:

            documents_response = session.get(
                evaluation["documents_url"],
                timeout=30
            )

            documents_response.raise_for_status()

            documents_soup = BeautifulSoup(
                documents_response.text,
                "html.parser"
            )

            print("\n" + "-" * 70)
            print("KP DOCUMENT PAGE DEBUG")
            print("-" * 70)

            print(
                "DOCUMENT PAGE TITLE:",
                documents_soup.title.get_text(strip=True)
                if documents_soup.title
                else None
            )

            print(
                "H4 HEADINGS:"
            )

            for heading in documents_soup.find_all("h4"):

                print(
                    "  ",
                    clean_text(
                        heading.get_text(
                            " ",
                            strip=True
                        )
                    )
                )

            print("\nDOWNLOAD LINKS:")

            for link in documents_soup.find_all(
                "a",
                href=True
            ):

                href = link.get(
                    "href",
                    ""
                )

                if (
                    "force_download.php" in href
                    or "Technical" in href
                    or "Comparative" in href
                    or "Financial" in href
                    or "Final" in href
                ):

                    print(
                        "  TEXT:",
                        clean_text(
                            link.get_text(
                                " ",
                                strip=True
                            )
                        )
                    )

                    print(
                        "  HREF:",
                        href
                    )

            print("-" * 70)

            documents = extract_document_information(
                documents_soup
            )

        except requests.RequestException as exc:

            print(
                "Failed to open KP "
                f"evaluation documents page: {exc}"
            )

    # --------------------------------------------------
    # Download individual documents
    # --------------------------------------------------

    for index, document in enumerate(
        documents,
        start=1
    ):

        pdf_url = document.get(
            "pdf_url"
        )

        if not pdf_url:
            continue

        document_name = (
            document.get(
                "document_name"
            )
            or f"document_{index}"
        )

        safe_name = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            document_name
        ).strip("_")

        if not safe_name:
            safe_name = (
                f"document_{index}"
            )

        pdf_path = download_pdf(
            session=session,
            pdf_url=pdf_url,
            tender_no=tender_no,
            filename=(
                f"{tender_no}_"
                f"{safe_name}.pdf"
            )
        )

        document["pdf_path"] = pdf_path

    # --------------------------------------------------
    # Build result
    # --------------------------------------------------

    result = {
        "evaluation_id": evaluation_id,

        "evaluation_date": None,

        "tender_no": (
            evaluation["tender_no"]
        ),

        "detail_url": (
            evaluation["documents_url"]
        ),

        "pdf_url": (
            evaluation["pdf_url"]
        ),

        "pdf_path": main_pdf_path,

        "detail_page_data": {
            "procurement_entity": (
                evaluation[
                    "procurement_entity"
                ]
            ),

            "description": (
                evaluation[
                    "description"
                ]
            ),

            "advertisement_date": (
                evaluation[
                    "advertisement_date"
                ]
            ),

            "closing_date": (
                evaluation[
                    "closing_date"
                ]
            ),

            "tender_id": (
                evaluation["tender_id"]
            ),

            "documents": documents,
        },

        "documents": documents,
    }

    # --------------------------------------------------
    # Print documents
    # --------------------------------------------------

    print("\nEvaluation Documents:")

    for document in documents:

        print(
            f"\n  Type: "
            f"{document.get('document_type')}"
        )

        print(
            f"  Name: "
            f"{document.get('document_name')}"
        )

        print(
            f"  Uploaded On: "
            f"{document.get('uploaded_on')}"
        )

        print(
            f"  PDF: "
            f"{document.get('pdf_url')}"
        )

        print(
            f"  Saved PDF: "
            f"{document.get('pdf_path')}"
        )

    print("\n" + "=" * 70)
    print("END KP PPRA EVALUATION SEARCH")
    print("=" * 70)

    return [result]


if __name__ == "__main__":

    tender_number = "32878"

    results = get_evaluations(
        tender_number
    )

    print("\nFINAL RESULT:")

    for result in results:

        print(result)