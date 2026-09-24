from pathlib import Path

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parent.parent

EXCEL_FILE = (
    BASE_DIR
    / "data"
    / "ICT_Projects_2026-27.xlsx"
)

PROJECT_SHEET = "Projects Details"


ICT_SERVICE_COLUMNS = [
    "Fixed Connectivity",
    "GSM / Devices",
    "Cloud",
    "Cyber Security",
    "Servers / Internet",
    "Fiber / Broadband",
    "CCTV Camera",
    "IoT",
    "SIMs (GSM/CMT)",
    "SMS / Messaging",
]


def get_workbook():
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Excel file not found: {EXCEL_FILE}"
        )

    return load_workbook(
        EXCEL_FILE,
        data_only=True
    )


def get_project_worksheet(wb):
    if PROJECT_SHEET not in wb.sheetnames:
        raise ValueError(
            f"Sheet '{PROJECT_SHEET}' not found"
        )

    return wb[PROJECT_SHEET]


def get_headers(ws):
    headers = []

    for cell in ws[1]:
        if cell.value is None:
            headers.append("")
        else:
            headers.append(
                str(cell.value).strip()
            )

    return headers


def normalize_value(value):
    """
    Convert Excel values into JSON-friendly values.
    Empty cells become None.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        return value

    return value


def get_required_services(project):
    """
    Return all ICT services/devices whose
    corresponding Excel column contains 'Yes'.
    """

    required_services = []

    for service in ICT_SERVICE_COLUMNS:
        value = project.get(service)

        if (
            isinstance(value, str)
            and value.strip().lower() == "yes"
        ):
            required_services.append(service)

    return required_services


def row_to_project(headers, row):
    """
    Convert one Excel row into a project dictionary.
    """

    project = {}

    for index, header in enumerate(headers):
        if not header:
            continue

        value = (
            row[index]
            if index < len(row)
            else None
        )

        project[header] = normalize_value(
            value
        )

    project["required_services"] = (
        get_required_services(project)
    )

    return project


def get_all_projects():
    """
    Return all projects from the
    ICT Projects - Consolidated sheet.
    """

    wb = get_workbook()

    try:
        ws = get_project_worksheet(wb)

        headers = get_headers(ws)

        projects = []

        for row in ws.iter_rows(
            min_row=2,
            values_only=True
        ):
            project = row_to_project(
                headers,
                row
            )

            project_name = project.get(
                "Project / Scheme Name"
            )

            if not project_name:
                continue

            projects.append(project)

        return projects

    finally:
        wb.close()


def get_project_by_id(project_id):
    """
    Return a single project using Project ID.
    """

    wb = get_workbook()

    try:
        ws = get_project_worksheet(wb)

        headers = get_headers(ws)

        project_id_header = "Project ID"

        if project_id_header not in headers:
            raise ValueError(
                "Column 'Project ID' not found"
            )

        project_id_index = headers.index(
            project_id_header
        )

        target_id = str(
            project_id
        ).strip()

        for row in ws.iter_rows(
            min_row=2,
            values_only=True
        ):
            current_id = (
                row[project_id_index]
                if project_id_index <
                len(row)
                else None
            )

            if current_id is None:
                continue

            if (
                str(current_id).strip()
                == target_id
            ):
                return row_to_project(
                    headers,
                    row
                )

        return None

    finally:
        wb.close()