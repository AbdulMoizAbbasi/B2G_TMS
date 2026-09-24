from database.connection import SessionLocal
from tender_scraper.storage.mysql_storage import insert_tender


db = SessionLocal()

try:
    tender = insert_tender(
        db,
        source_id=1,
        web_tender_no="TEST-001",
        tender_reference_no="TEST-REF-001",
        tender_name="Test Tender - DELETE ME",
        city="Islamabad",
        authority="Test Authority",
        organization="Test Organization",
        estimated_value=1000000,
        estimated_value_source="test",
        raw_data={
            "test": True,
            "source": "development",
        },
    )

    print("Tender inserted successfully.")
    print(f"jazzid: {tender.jazzid}")
    print(f"name: {tender.tender_name}")

finally:
    db.close()