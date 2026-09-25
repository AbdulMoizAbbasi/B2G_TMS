from pathlib import Path
from datetime import datetime, timezone

import requests


REQUEST_TIMEOUT = 60

DOCUMENTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "documents"
)


def download_document(
    url: str,
    *,
    source: str,
    tender_key: str,
    document_name: str = "document.pdf",
) -> dict:
    """
    Download one tender document to the local filesystem.

    Returns metadata describing the download result.
    """

    if not url:
        raise ValueError("Document URL is required.")

    source_folder = source.lower().replace(" ", "_")
    tender_folder = DOCUMENTS_DIR / source_folder / tender_key

    tender_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = tender_folder / document_name

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        file_path.write_bytes(response.content)

        file_size = file_path.stat().st_size

        backend_root = Path(__file__).resolve().parent.parent.parent

        relative_path = file_path.relative_to(backend_root)

        return {
            "download_status": "DOWNLOADED",
            "local_path": relative_path.as_posix(),
            "file_size": file_size,
            "downloaded_at": datetime.now(timezone.utc),
        }

    except requests.RequestException:
        return {
            "download_status": "FAILED",
            "local_path": None,
            "file_size": None,
            "downloaded_at": None,
        }



def get_sindh_document_metadata(published_document_id):
    """
    Fetch Sindh PPRA document metadata using publishedDocumentID.
    """

    url = (
        "https://apiprd.eprocure.gov.pk/"
        "websiteportal/publicportal/1.0.0/api/v1/publicportal/"
        "getallpublisheddocumentdetailbypdid"
    )

    payload = {
        "Id": published_document_id,
        "loggedInUserID": 1,
        "loggedInUserOfficeID": 1,
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "authorization": "Basic YWRtaW46cHByYTEy",
            "officedetail": "Sindh-PPRA-Dev",
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    records = data.get(
        "data",
        [],
    )

    if not records:
        return None

    record = records[0]

    return {
        "file_id": record.get("dmS_FileID"),
        "file_guid": record.get("dmS_FileGUID"),
    }


def download_sindh_document(
    file_id,
    file_guid,
    *,
    tender_key,
    document_name="Bidding Document.pdf",
):
    """
    Download a Sindh PPRA document using DMS file ID and GUID.
    """

    url = (
        "https://apiprd.eprocure.gov.pk/"
        "documentmanagementsystem/dmspublicapi/1.0.0/api/v1/"
        "dmspublicapi/downloadportalfilebyguid"
    )

    payload = {
        "loggedInUserOfficeID": 31640,
        "loggedInUserID": 1,
        "ID": file_id,
        "idsList": file_guid,
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "authorization": "Basic YWRtaW46cHByYTEy",
        "officedetail": "Sindh-PPRA-Dev",
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    source_folder = "sindh_ppra"

    tender_folder = (
        DOCUMENTS_DIR
        / source_folder
        / str(tender_key)
    )

    tender_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        tender_folder
        / document_name
    )

    with open(
        file_path,
        "wb",
    ) as file:
        file.write(
            response.content
        )

    return {
        "local_path": str(
            file_path.relative_to(
                DOCUMENTS_DIR.parent
            )
        ).replace("\\", "/"),
        "download_status": "DOWNLOADED",
        "file_size": len(
            response.content
        ),
        "downloaded_at": datetime.utcnow(),
    }