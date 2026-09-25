from sqlalchemy.orm import Session

from database.models.tender import Tender
from database.models.tender_relevance import TenderRelevance
from database.models.tender_document import TenderDocument
from database.models.tender_participation import TenderParticipation





def insert_participation(
    db: Session,
    *,
    tender_jazzid: int,
    status: str = "NOT_REVIEWED",
    decided_by: int | None = None,
    decided_at=None,
    delegated_employee_id: int | None = None,
) -> TenderParticipation:

    participation = TenderParticipation(
        tender_jazzid=tender_jazzid,
        status=status,
        decided_by=decided_by,
        decided_at=decided_at,
        delegated_employee_id=delegated_employee_id,
    )

    db.add(participation)
    db.commit()
    db.refresh(participation)

    return participation

def insert_document(
    db: Session,
    *,
    tender_jazzid: int,
    document_type: str,
    document_name: str | None = None,
    source_url: str | None = None,
    local_path: str | None = None,
    download_status: str = "PENDING",
    file_size: int | None = None,
    downloaded_at=None,
) -> TenderDocument:

    document = TenderDocument(
        tender_jazzid=tender_jazzid,
        document_type=document_type,
        document_name=document_name,
        source_url=source_url,
        local_path=local_path,
        download_status=download_status,
        file_size=file_size,
        downloaded_at=downloaded_at,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

def insert_relevance(
    db: Session,
    *,
    tender_jazzid: int,
    keyword_score=0,
    matched_keywords: list | None = None,
    matched_capabilities: list | None = None,
    relevance_reason: str | None = None,
) -> TenderRelevance:

    relevance = TenderRelevance(
        tender_jazzid=tender_jazzid,
        keyword_score=keyword_score,
        matched_keywords=matched_keywords,
        matched_capabilities=matched_capabilities,
        relevance_reason=relevance_reason,
    )

    db.add(relevance)
    db.commit()
    db.refresh(relevance)

    return relevance


def insert_tender(
    db: Session,
    *,
    source_id: int,
    web_tender_no: str | None = None,
    tender_reference_no: str | None = None,
    tender_name: str | None = None,
    city: str | None = None,
    authority: str | None = None,
    organization: str | None = None,
    estimated_value=None,
    estimated_value_source: str | None = None,
    advertised_date=None,
    closed_date=None,
    source_detail_url: str | None = None,
    primary_document_url: str | None = None,
    raw_data: dict | None = None,
) -> Tender:

    tender = Tender(
        source_id=source_id,
        web_tender_no=web_tender_no,
        tender_reference_no=tender_reference_no,
        tender_name=tender_name,
        city=city,
        authority=authority,
        organization=organization,
        estimated_value=estimated_value,
        estimated_value_source=estimated_value_source,
        advertised_date=advertised_date,
        closed_date=closed_date,
        source_detail_url=source_detail_url,
        primary_document_url=primary_document_url,
        raw_data=raw_data,
    )

    db.add(tender)
    db.commit()
    db.refresh(tender)

    return tender



def persist_tender(
    db: Session,
    *,
    mapped_tender: dict,
    relevance: dict,
) -> Tender:
    """
    Persist one tender, its relevance, and its documents
    in a single database transaction.

    If any part fails, the entire transaction is rolled back.
    """

    try:
        # ----------------------------------------------------
        # 1. Insert tender
        # ----------------------------------------------------

        tender = Tender(
            source_id=mapped_tender["source_id"],
            web_tender_no=mapped_tender.get("web_tender_no"),
            tender_reference_no=mapped_tender.get(
                "tender_reference_no"
            ),
            tender_name=mapped_tender.get("tender_name"),
            city=mapped_tender.get("city"),
            authority=mapped_tender.get("authority"),
            organization=mapped_tender.get("organization"),
            estimated_value=mapped_tender.get(
                "estimated_value"
            ),
            estimated_value_source=mapped_tender.get(
                "estimated_value_source"
            ),
            advertised_date=mapped_tender.get(
                "advertised_date"
            ),
            closed_date=mapped_tender.get(
                "closed_date"
            ),
            source_detail_url=mapped_tender.get(
                "source_detail_url"
            ),
            primary_document_url=mapped_tender.get(
                "primary_document_url"
            ),
            raw_data=mapped_tender.get("raw_data"),
        )

        db.add(tender)

        # Send INSERT to the database so that
        # the AUTO_INCREMENT jazzid is available.
        db.flush()

        # ----------------------------------------------------
        # 2. Insert relevance
        # ----------------------------------------------------

        tender_relevance = TenderRelevance(
            tender_jazzid=tender.jazzid,
            keyword_score=relevance.get(
                "keyword_score",
                0,
            ),
            matched_keywords=relevance.get(
                "matched_keywords",
                [],
            ),
            matched_capabilities=relevance.get(
                "matched_capabilities",
                [],
            ),
            relevance_reason=relevance.get(
                "relevance_reason"
            ),
        )

        db.add(tender_relevance)

        # ----------------------------------------------------
        # 3. Insert documents
        # ----------------------------------------------------

        documents = mapped_tender.get(
            "documents",
            [],
        )

        for document_data in documents:

            document = TenderDocument(
                tender_jazzid=tender.jazzid,
                document_type=document_data.get(
                    "document_type",
                    "PRIMARY",
                ),
                document_name=document_data.get(
                    "document_name"
                ),
                source_url=document_data.get(
                    "source_url"
                ),
                local_path=document_data.get(
                    "local_path"
                ),
                download_status=document_data.get(
                    "download_status",
                    "PENDING",
                ),
                file_size=document_data.get(
                    "file_size"
                ),
                downloaded_at=document_data.get(
                    "downloaded_at"
                ),
            )

            db.add(document)

        # ----------------------------------------------------
        # 4. Commit everything together
        # ----------------------------------------------------

        db.commit()
        db.refresh(tender)

        return tender

    except Exception:
        db.rollback()
        raise