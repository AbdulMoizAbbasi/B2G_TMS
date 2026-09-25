from datetime import datetime

from database.connection import SessionLocal
from database.models.tender import Tender
from database.models.tender_source import TenderSource
from database.models.tender_relevance import TenderRelevance
from database.models.tender_document import TenderDocument


db = SessionLocal()

try:
    source = (
        db.query(TenderSource)
        .filter(TenderSource.id == 1)
        .first()
    )

    if source is None:
        raise RuntimeError("Tender source 1 not found")

    tender = Tender(
        source_id=source.id,
        web_tender_no="DELETE-TEST-001",
        tender_reference_no="DELETE-TEST-001",
        tender_name="TEMPORARY DELETE TEST TENDER",
        city="Test City",
        authority="Test Authority",
        organization="Test Organization",
        advertised_date=datetime.now(),
        closed_date=datetime.now(),
        raw_data={"test": True},
    )

    db.add(tender)
    db.flush()

    relevance = TenderRelevance(
        tender_jazzid=tender.jazzid,
        keyword_score=0,
        matched_keywords=[],
        matched_capabilities=[],
    )

    document = TenderDocument(
        tender_jazzid=tender.jazzid,
        document_type="PRIMARY",
        document_name="delete-test.pdf",
        source_url="https://example.com/delete-test.pdf",
        local_path="test/delete-test.pdf",
        download_status="PENDING",
    )

    db.add(relevance)
    db.add(document)

    db.commit()

    print("Temporary tender created successfully")
    print("JAZZID:", tender.jazzid)

except Exception:
    db.rollback()
    raise

finally:
    db.close()