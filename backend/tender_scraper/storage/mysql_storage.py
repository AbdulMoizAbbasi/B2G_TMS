from sqlalchemy.orm import Session

from database.models.tender import Tender
from database.models.tender_source import TenderSource
from database.models.tender_relevance import TenderRelevance
from database.models.tender_document import TenderDocument
from database.models.tender_participation import TenderParticipation
from database.models.tender_region_assignment import TenderRegionAssignment
from database.models.region import Region

from tender_scraper.storage.region_mapper import get_region_name


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
):
    """
    Insert a new tender or update an existing tender.

    Tender identity:
        - Punjab PPRA:
            source + tender_name + organization
            + primary_document_url
        - All other sources:
            source + web_tender_no

    Source is resolved by source_name.

    Region:
        - Automatically determined from source + city.
        - New tenders receive an AUTO region assignment.
        - Existing ADMIN region assignments are preserved.
        - Existing AUTO assignments are updated when the
          automatically determined region changes.

    Scraper-owned data is updated on every run.

    Application-owned data such as participation and
    admin overrides is not modified here.

    Relevance and primary documents are synchronized.
    """

    created = False

    try:
        # ----------------------------------------------------
        # 1. Resolve source name to database source ID
        # ----------------------------------------------------

        source_name = mapped_tender["source_name"]

        source = (
            db.query(TenderSource)
            .filter(
                TenderSource.name == source_name
            )
            .first()
        )

        if source is None:
            raise ValueError(
                f"Unknown tender source: {source_name}"
            )

        source_id = source.id

        web_tender_no = mapped_tender.get(
            "web_tender_no"
        )

        tender_name = mapped_tender.get(
            "tender_name"
        )

        city = mapped_tender.get(
            "city"
        )

        # ----------------------------------------------------
        # 2. Determine automatic region
        # ----------------------------------------------------

        region_name = get_region_name(
            source_name=source_name,
            city=city,
        )

        automatic_region = None

        if region_name is not None:

            automatic_region = (
                db.query(Region)
                .filter(
                    Region.name == region_name
                )
                .first()
            )

            if automatic_region is None:
                raise ValueError(
                    f"Region '{region_name}' "
                    f"does not exist in the database."
                )

        # ----------------------------------------------------
        # 3. Find existing tender
        # ----------------------------------------------------

        if source_name == "Punjab PPRA":

            # Punjab PPRA identity:
            # source + tender_name + organization
            # + primary_document_url

            tender = (
                db.query(Tender)
                .filter(
                    Tender.source_id == source_id,
                    Tender.tender_name == tender_name,
                    Tender.organization
                    == mapped_tender.get(
                        "organization"
                    ),
                    Tender.primary_document_url
                    == mapped_tender.get(
                        "primary_document_url"
                    ),
                )
                .first()
            )

        else:

            if web_tender_no:

                tender = (
                    db.query(Tender)
                    .filter(
                        Tender.source_id
                        == source_id,
                        Tender.web_tender_no
                        == web_tender_no,
                    )
                    .first()
                )

            else:

                tender = None

        # ----------------------------------------------------
        # 4. Create or update tender
        # ----------------------------------------------------

        if tender is None:

            created = True

            tender = Tender(
                source_id=source_id,
                region_id=(
                    automatic_region.id
                    if automatic_region
                    else None
                ),
                web_tender_no=web_tender_no,
                tender_reference_no=mapped_tender.get(
                    "tender_reference_no"
                ),
                tender_name=tender_name,
                city=city,
                authority=mapped_tender.get(
                    "authority"
                ),
                organization=mapped_tender.get(
                    "organization"
                ),
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
                raw_data=mapped_tender.get(
                    "raw_data"
                ),
            )

            db.add(tender)
            db.flush()

            # ------------------------------------------------
            # Create AUTO region assignment for new tender
            # ------------------------------------------------

            if automatic_region:

                region_assignment = (
                    TenderRegionAssignment(
                        tender_jazzid=tender.jazzid,
                        region_id=automatic_region.id,
                        assignment_type="AUTO",
                        assigned_by=None,
                    )
                )

                db.add(region_assignment)

        else:

            tender.web_tender_no = web_tender_no

            tender.tender_reference_no = (
                mapped_tender.get(
                    "tender_reference_no"
                )
            )

            tender.tender_name = tender_name

            tender.city = city

            tender.authority = mapped_tender.get(
                "authority"
            )

            tender.organization = (
                mapped_tender.get(
                    "organization"
                )
            )

            tender.estimated_value = (
                mapped_tender.get(
                    "estimated_value"
                )
            )

            tender.estimated_value_source = (
                mapped_tender.get(
                    "estimated_value_source"
                )
            )

            tender.advertised_date = (
                mapped_tender.get(
                    "advertised_date"
                )
            )

            tender.closed_date = (
                mapped_tender.get(
                    "closed_date"
                )
            )

            tender.source_detail_url = (
                mapped_tender.get(
                    "source_detail_url"
                )
            )

            tender.primary_document_url = (
                mapped_tender.get(
                    "primary_document_url"
                )
            )

            tender.raw_data = (
                mapped_tender.get(
                    "raw_data"
                )
            )

            # ------------------------------------------------
            # Preserve ADMIN region override
            # ------------------------------------------------

            admin_assignment = (
                db.query(TenderRegionAssignment)
                .filter(
                    TenderRegionAssignment.tender_jazzid
                    == tender.jazzid,
                    TenderRegionAssignment.assignment_type
                    == "ADMIN",
                )
                .order_by(
                    TenderRegionAssignment.assigned_at.desc()
                )
                .first()
            )

            if admin_assignment:

                # Admin has explicitly assigned this tender.
                # Never overwrite it during scraping.

                if (
                    tender.region_id
                    != admin_assignment.region_id
                ):
                    tender.region_id = (
                        admin_assignment.region_id
                    )

            else:

                # ------------------------------------------------
                # No ADMIN override exists.
                # Use automatic region mapping.
                # ------------------------------------------------

                if automatic_region:

                    tender.region_id = (
                        automatic_region.id
                    )

                    # Find the latest AUTO assignment
                    auto_assignment = (
                        db.query(
                            TenderRegionAssignment
                        )
                        .filter(
                            TenderRegionAssignment
                            .tender_jazzid
                            == tender.jazzid,
                            TenderRegionAssignment
                            .assignment_type
                            == "AUTO",
                        )
                        .order_by(
                            TenderRegionAssignment
                            .assigned_at.desc()
                        )
                        .first()
                    )

                    if auto_assignment is None:

                        auto_assignment = (
                            TenderRegionAssignment(
                                tender_jazzid=(
                                    tender.jazzid
                                ),
                                region_id=(
                                    automatic_region.id
                                ),
                                assignment_type="AUTO",
                                assigned_by=None,
                            )
                        )

                        db.add(
                            auto_assignment
                        )

                    elif (
                        auto_assignment.region_id
                        != automatic_region.id
                    ):

                        # Region changed automatically.
                        # Keep the assignment history by
                        # adding a new AUTO assignment.

                        new_auto_assignment = (
                            TenderRegionAssignment(
                                tender_jazzid=(
                                    tender.jazzid
                                ),
                                region_id=(
                                    automatic_region.id
                                ),
                                assignment_type="AUTO",
                                assigned_by=None,
                            )
                        )

                        db.add(
                            new_auto_assignment
                        )

                else:

                    # Unknown/missing region.
                    #
                    # For an existing tender with no ADMIN
                    # override, leave the current region as-is
                    # rather than destroying a previous assignment.

                    pass

            db.flush()

        # ----------------------------------------------------
        # 5. Relevance
        # ----------------------------------------------------

        tender_relevance = (
            db.query(TenderRelevance)
            .filter(
                TenderRelevance.tender_jazzid
                == tender.jazzid
            )
            .first()
        )

        if tender_relevance is None:

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

        else:

            tender_relevance.keyword_score = (
                relevance.get(
                    "keyword_score",
                    0,
                )
            )

            tender_relevance.matched_keywords = (
                relevance.get(
                    "matched_keywords",
                    [],
                )
            )

            tender_relevance.matched_capabilities = (
                relevance.get(
                    "matched_capabilities",
                    [],
                )
            )

            tender_relevance.relevance_reason = (
                relevance.get(
                    "relevance_reason"
                )
            )

        # ----------------------------------------------------
        # 6. Documents
        # ----------------------------------------------------

        documents = mapped_tender.get(
            "documents",
            [],
        )

        for document_data in documents:

            document_type = document_data.get(
                "document_type",
                "PRIMARY",
            )

            source_url = document_data.get(
                "source_url"
            )

            document = (
                db.query(TenderDocument)
                .filter(
                    TenderDocument.tender_jazzid
                    == tender.jazzid,
                    TenderDocument.document_type
                    == document_type,
                )
                .first()
            )

            if document is None:

                document = TenderDocument(
                    tender_jazzid=tender.jazzid,
                    document_type=document_type,
                    document_name=document_data.get(
                        "document_name"
                    ),
                    source_url=source_url,
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

            else:

                document.document_name = (
                    document_data.get(
                        "document_name"
                    )
                )

                document.source_url = source_url

                if document_data.get(
                    "local_path"
                ) is not None:

                    document.local_path = (
                        document_data.get(
                            "local_path"
                        )
                    )

                if document_data.get(
                    "download_status"
                ) is not None:

                    document.download_status = (
                        document_data.get(
                            "download_status"
                        )
                    )

                if document_data.get(
                    "file_size"
                ) is not None:

                    document.file_size = (
                        document_data.get(
                            "file_size"
                        )
                    )

                if document_data.get(
                    "downloaded_at"
                ) is not None:

                    document.downloaded_at = (
                        document_data.get(
                            "downloaded_at"
                        )
                    )

        # ----------------------------------------------------
        # 7. Commit
        # ----------------------------------------------------

        db.commit()
        db.refresh(tender)

        action = (
            "CREATED"
            if created
            else "UPDATED"
        )

        if action == "UPDATED":

            print(
                f"[MYSQL UPDATED] "
                f"web_tender_no={tender.web_tender_no} | "
                f"name={tender.tender_name} | "
                f"organization={tender.organization}"
            )

        return {
            "tender": tender,
            "action": action,
        }

    except Exception:

        db.rollback()
        raise