from sqlalchemy.orm import Session

from database.models.tender import Tender


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