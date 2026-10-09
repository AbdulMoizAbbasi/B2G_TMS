from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import threading
from fastapi import Header
from pathlib import Path
from config.paths import (DATA_DIR, DOCUMENTS_DIR, CHECKPOINT_FILE,)

from sqlalchemy import func, or_, case
from sqlalchemy.orm import Session, joinedload
import mimetypes

import jwt
import os
from database.connection import SessionLocal
from database.models.user import User
from database.models.coordinator import Coordinator
from database.models.tender_source import TenderSource
from database.models.tender_relevance import TenderRelevance
from database.models.tender import Tender
from database.models.tender_field_override import TenderFieldOverride
from database.models.tender_document import TenderDocument
from database.models.tender_participation import TenderParticipation
from database.models.employee import Employee
from database.models.product import Product
from database.models.tender_region_assignment import TenderRegionAssignment
from database.models.region import Region
from tender_scraper.storage.document_downloader import download_document

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Literal
from fastapi import BackgroundTasks
from tender_scraper.orchestrator_tenderfetch import main as run_tender_scraper



from tender_scraper.local_import_processor import (
    process_local_punjab_tenders,
    process_local_balochistan_tenders,
)

from auth import (
    verify_password,
    create_access_token,
    decode_access_token,
)

# ============================================================
# SCRAPER EXECUTION STATE
# ============================================================
document_download_locks = {}
document_download_locks_lock = threading.Lock()
scraper_lock = threading.Lock()
scraper_running = False

app = FastAPI(
    title="JazzWorld B2G Tender Portal"
)





def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()



def require_alert_service_key(
    x_alert_service_key: str | None = Header(default=None),
):
    expected_key = os.getenv("ALERT_SERVICE_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="Alert service key is not configured.",
        )

    if x_alert_service_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid alert service key.",
        )

    return True


def get_document_download_lock(jazzid: int):
    with document_download_locks_lock:
        if jazzid not in document_download_locks:
            document_download_locks[jazzid] = threading.Lock()

        return document_download_locks[jazzid]
    


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = decode_access_token(token)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
        )

    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    return user

def require_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return current_user


def require_coordinator(
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "COORDINATOR":
        raise HTTPException(
            status_code=403,
            detail="Coordinator access required",
        )

    return current_user


def require_viewer(
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "VIEWER":
        raise HTTPException(
            status_code=403,
            detail="Viewer access required",
        )

    return current_user


def get_coordinator_region(
    current_user: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    coordinator = (
        db.query(Coordinator)
        .filter(Coordinator.user_id == current_user.id)
        .first()
    )

    if coordinator is None:
        raise HTTPException(
            status_code=403,
            detail="Coordinator region is not configured",
        )

    return coordinator.region_id


class LoginRequest(BaseModel):
    username: str
    password: str

class TenderUpdateRequest(BaseModel):
    web_tender_no: str | None = None
    tender_reference_no: str | None = None
    tender_name: str | None = None
    city: str | None = None
    authority: str | None = None
    organization: str | None = None
    estimated_value: Decimal | None = None
    advertised_date: datetime | None = None
    closed_date: datetime | None = None
    relevance_score: Decimal | None = None

class TenderParticipationRequest(BaseModel):
    status: Literal[
        "NOT_REVIEWED",
        "ENGAGING",
        "PARTICIPATED",
        "NOT_PARTICIPATING",
    ]
    employee_id: int | None = None
    product_ids: list[int] | None = None

class TenderDelegationRequest(BaseModel):
    employee_id: int


class TenderRegionUpdateRequest(BaseModel):
    region_id: int

class BulkTenderDeleteRequest(BaseModel):
    jazzids: list[int]


class ScraperImportRequest(BaseModel):
    portal: str
    tenders: List[Dict[str, Any]]


@app.get("/")
def root():
    return {
        "message": "Tender Management System API is running"
    }

@app.post("/api/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.name,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role.name,
        },
    }


@app.get("/api/auth/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.name,
        "is_active": current_user.is_active,
    }




@app.get("/api/tenders")
def get_tenders(
    page: int = 1,
    page_size: int = 10,
    tender_no: str | None = None,
    tender_name: str | None = None,
    city: str | None = None,
    organization: str | None = None,
    submission_date_from: str | None = None,
    submission_date_to: str | None = None,
    advertised_date_from: str | None = None,
    advertised_date_to: str | None = None,
    estimated_value_min: float | None = None,
    estimated_value_max: float | None = None,
    score_min: float | None = None,
    score_max: float | None = None,
    participation_status: list[str] | None = Query(default=None),
    product: list[str] | None = Query(default=None),
    source: list[str] | None = Query(default=None),
    region: list[str] | None = Query(default=None),
    sort_by: str = "submissionDate",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate pagination
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than or equal to 1.")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100.")

    # Validate sorting
    allowed_sort_fields = {"submissionDate", "estimatedValue", "tenderName", "city"}
    if sort_by not in allowed_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_order must be either 'asc' or 'desc'.")

    # Validate numeric ranges
    if estimated_value_min is not None and estimated_value_max is not None and estimated_value_min > estimated_value_max:
        raise HTTPException(status_code=400, detail="estimated_value_min cannot exceed estimated_value_max.")
    if score_min is not None and score_min < 0:
        raise HTTPException(status_code=400, detail="score_min cannot be negative.")
    if score_max is not None and score_max < 0:
        raise HTTPException(status_code=400, detail="score_max cannot be negative.")
    if score_min is not None and score_max is not None and score_min > score_max:
        raise HTTPException(status_code=400, detail="score_min cannot exceed score_max.")

    # Validate multi-select filters
    allowed_statuses = {"NOT_REVIEWED", "ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING"}
    allowed_regions = {"North1", "North2", "Central", "South"}

    if participation_status:
        invalid = set(participation_status) - allowed_statuses
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid participation status: {sorted(invalid)}")
    if region:
        invalid = set(region) - allowed_regions
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid region: {sorted(invalid)}")

    # Base query
    query = (
        db.query(Tender)
        .outerjoin(TenderRelevance, TenderRelevance.tender_jazzid == Tender.jazzid)
        .outerjoin(TenderFieldOverride, TenderFieldOverride.tender_jazzid == Tender.jazzid)
        .outerjoin(TenderParticipation, TenderParticipation.tender_jazzid == Tender.jazzid)
        .join(TenderSource, Tender.source_id == TenderSource.id)
        .outerjoin(Region, Tender.region_id == Region.id)
    )

    # Coordinator access restrictions
    coordinator = None
    if current_user.role.name == "COORDINATOR":
        coordinator = db.query(Coordinator).filter(Coordinator.user_id == current_user.id).first()
        if coordinator is None:
            raise HTTPException(status_code=403, detail="Coordinator region is not configured.")
        query = query.filter(Tender.region_id == coordinator.region_id, TenderRelevance.keyword_score > 0)

    # Effective fields: Admin overrides take precedence
    effective_tender_no = func.coalesce(TenderFieldOverride.web_tender_no, Tender.web_tender_no)
    effective_tender_name = func.coalesce(TenderFieldOverride.tender_name, Tender.tender_name)
    effective_city = func.coalesce(TenderFieldOverride.city, Tender.city)
    effective_organization = func.coalesce(TenderFieldOverride.organization, Tender.organization)
    effective_estimated_value = func.coalesce(TenderFieldOverride.estimated_value, Tender.estimated_value)
    effective_closed_date = func.coalesce(TenderFieldOverride.closed_date, Tender.closed_date)
    effective_advertised_date = func.coalesce(TenderFieldOverride.advertised_date, Tender.advertised_date)

    # Text filters
    if tender_no and tender_no.strip():
        query = query.filter(effective_tender_no.ilike(f"%{tender_no.strip()}%"))
    if tender_name and tender_name.strip():
        query = query.filter(effective_tender_name.ilike(f"%{tender_name.strip()}%"))
    if city and city.strip():
        query = query.filter(effective_city.ilike(f"%{city.strip()}%"))
    if organization and organization.strip():
        query = query.filter(effective_organization.ilike(f"%{organization.strip()}%"))

    # Source: match ANY selected source
    if source:
        query = query.filter(TenderSource.name.in_([value.strip() for value in source if value.strip()]))
    # Region: match ANY selected region
    if region:
        query = query.filter(Region.name.in_(region))

    # Submission/closing date range
    if submission_date_from:
        try:
            date_from = datetime.strptime(submission_date_from, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="submission_date_from must use YYYY-MM-DD format.")
        query = query.filter(effective_closed_date >= date_from)

    if submission_date_to:
        try:
            date_to = datetime.strptime(submission_date_to, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="submission_date_to must use YYYY-MM-DD format.")
        query = query.filter(effective_closed_date < date_to)

    # Advertised date range
    if advertised_date_from:
        try:
            date_from = datetime.strptime(advertised_date_from, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="advertised_date_from must use YYYY-MM-DD format.")
        query = query.filter(effective_advertised_date >= date_from)

    if advertised_date_to:
        try:
            date_to = datetime.strptime(advertised_date_to, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="advertised_date_to must use YYYY-MM-DD format.")
        query = query.filter(effective_advertised_date < date_to)

    # Estimated value range
    if estimated_value_min is not None:
        query = query.filter(effective_estimated_value >= estimated_value_min)
    if estimated_value_max is not None:
        query = query.filter(effective_estimated_value <= estimated_value_max)

    # Relevance score range
    if score_min is not None:
        query = query.filter(TenderRelevance.keyword_score >= score_min)
    if score_max is not None:
        query = query.filter(TenderRelevance.keyword_score <= score_max)

    # Participation status: match ANY selected status
    if participation_status:
        status_conditions = []
        if "NOT_REVIEWED" in participation_status:
            status_conditions.append(or_(
                TenderParticipation.id.is_(None),
                TenderParticipation.status == "NOT_REVIEWED",
            ))
        if "ENGAGING" in participation_status:
            status_conditions.append(TenderParticipation.status.in_(["ENGAGING", "PARTICIPATING"]))
        if "PARTICIPATED" in participation_status:
            status_conditions.append(TenderParticipation.status == "PARTICIPATED")
        if "NOT_PARTICIPATING" in participation_status:
            status_conditions.append(TenderParticipation.status == "NOT_PARTICIPATING")
        if status_conditions:
            query = query.filter(or_(*status_conditions))

    # Product/capability: match ANY selected value in matched_capabilities JSON
    if product:
        product_conditions = [
            func.json_contains(TenderRelevance.matched_capabilities, func.json_quote(value.strip())) == 1
            for value in product if value.strip()
        ]
        if product_conditions:
            query = query.filter(or_(*product_conditions))

    # Count matching records before pagination
    total = query.with_entities(func.count(Tender.jazzid)).scalar() or 0

    # Sorting
    sort_columns = {
        "submissionDate": effective_closed_date,
        "estimatedValue": effective_estimated_value,
        "tenderName": effective_tender_name,
        "city": effective_city,
    }
    sort_column = sort_columns[sort_by]
    query = query.order_by(
        sort_column.asc() if sort_order == "asc" else sort_column.desc(),
        Tender.jazzid.desc(),
    )

    # Pagination and eager loading
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(
        joinedload(Tender.source),
        joinedload(Tender.region),
        joinedload(Tender.relevance),
        joinedload(Tender.participation),
        joinedload(Tender.field_override),
    )
    tenders = query.all()
    total_pages = (total + page_size - 1) // page_size if total else 0

    # Build result
    result = []
    for tender in tenders:
        override = tender.field_override
        participation = tender.participation
        relevance = tender.relevance

        result.append({
            "jazzid": tender.jazzid,
            "source_id": tender.source_id,
            "source": tender.source.name if tender.source else None,
            "region": tender.region.name if tender.region else None,
            "web_tender_no": override.web_tender_no if override and override.web_tender_no is not None else tender.web_tender_no,
            "tender_reference_no": override.tender_reference_no if override and override.tender_reference_no is not None else tender.tender_reference_no,
            "tender_name": override.tender_name if override and override.tender_name is not None else tender.tender_name,
            "city": override.city if override and override.city is not None else tender.city,
            "authority": override.authority if override and override.authority is not None else tender.authority,
            "organization": override.organization if override and override.organization is not None else tender.organization,
            "estimated_value": float(override.estimated_value if override and override.estimated_value is not None else tender.estimated_value) if (override and override.estimated_value is not None) or tender.estimated_value is not None else None,
            "advertised_date": override.advertised_date if override and override.advertised_date is not None else tender.advertised_date,
            "closed_date": override.closed_date if override and override.closed_date is not None else tender.closed_date,
            "source_detail_url": tender.source_detail_url,
            "primary_document_url": tender.primary_document_url,
            "keywords_matched": relevance.matched_keywords if relevance else [],
            "relevance_score": float(relevance.keyword_score) if relevance and relevance.keyword_score is not None else 0,
            "matched_capabilities": relevance.matched_capabilities if relevance else [],
            "participation_status": participation.status if participation else "NOT_REVIEWED",
        })

    # Summary query: intentionally ignores table filters
    summary_query = (
        db.query(Tender)
        .outerjoin(TenderRelevance, TenderRelevance.tender_jazzid == Tender.jazzid)
        .outerjoin(TenderParticipation, TenderParticipation.tender_jazzid == Tender.jazzid)
    )

    if coordinator is not None:
        summary_query = summary_query.filter(
            Tender.region_id == coordinator.region_id,
            TenderRelevance.keyword_score > 0,
        )

    summary_total = summary_query.with_entities(func.count(Tender.jazzid)).scalar() or 0
    review_pending_count = summary_query.filter(or_(
        TenderParticipation.id.is_(None),
        TenderParticipation.status == "NOT_REVIEWED",
    )).with_entities(func.count(Tender.jazzid)).scalar() or 0
    participating_count = summary_query.filter(
        TenderParticipation.status.in_(["ENGAGING", "PARTICIPATED"])
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0
    not_participating_count = summary_query.filter(
        TenderParticipation.status == "NOT_PARTICIPATING"
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    next_three_days = today_start + timedelta(days=4)
    closing_soon_count = summary_query.filter(
        Tender.closed_date >= today_start,
        Tender.closed_date < next_three_days,
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0

    return {
        "items": result,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        "summary": {
            "total": summary_total,
            "review_pending": review_pending_count,
            "participating": participating_count,
            "not_participating": not_participating_count,
            "closing_soon": closing_soon_count,
        },
    }


@app.get("/api/regions")
def get_regions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    regions = (
        db.query(Region)
        .order_by(Region.name.asc())
        .all()
    )

    return [
        {
            "id": region.id,
            "name": region.name,
        }
        for region in regions
    ]



@app.patch("/api/tenders/{jazzid}/region")
def update_tender_region(
    jazzid: int,
    request: TenderRegionUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == jazzid)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    region = (
        db.query(Region)
        .filter(Region.id == request.region_id)
        .first()
    )

    if region is None:
        raise HTTPException(
            status_code=404,
            detail="Region not found",
        )

    # Update the effective region.
    tender.region_id = region.id

    # Record the admin override.
    assignment = TenderRegionAssignment(
        tender_jazzid=tender.jazzid,
        region_id=region.id,
        assignment_type="ADMIN",
        assigned_by=current_user.id,
        assigned_at=datetime.now(timezone.utc),
    )

    db.add(assignment)

    db.commit()
    db.refresh(tender)

    return {
        "message": "Tender region updated successfully",
        "jazzid": tender.jazzid,
        "region_id": region.id,
        "region": region.name,
        "updated_by": current_user.username,
        "assignment_type": "ADMIN",
    }



@app.get("/api/tenders/{jazzid}")
def get_tender(
    jazzid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Tender)
        .join(
            TenderSource,
            Tender.source_id == TenderSource.id,
        )
        .outerjoin(
            TenderRelevance,
            TenderRelevance.tender_jazzid == Tender.jazzid,
        )
        .outerjoin(
            TenderFieldOverride,
            TenderFieldOverride.tender_jazzid == Tender.jazzid,
        )
        .filter(
            Tender.jazzid == jazzid
        )
    )

    if current_user.role.name == "COORDINATOR":
        coordinator = (
            db.query(Coordinator)
            .filter(
                Coordinator.user_id == current_user.id
            )
            .first()
        )

        if coordinator is None:
            raise HTTPException(
                status_code=403,
                detail="Coordinator region is not configured",
            )

        query = query.filter(
            Tender.region_id == coordinator.region_id,
            TenderRelevance.keyword_score > 0,
        )

    tender = query.first()

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    override = tender.field_override
    document = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.tender_jazzid == tender.jazzid,
            TenderDocument.document_type == "PRIMARY",
        )
        .first()
    )

    document_available = (
        document is not None
        and document.download_status == "DOWNLOADED"
    )

    return {
        "jazzid": tender.jazzid,
        "source_id": tender.source_id,
        "source": tender.source.name,
        "region": tender.region.name if tender.region else None,

        "web_tender_no": (
            override.web_tender_no
            if override and override.web_tender_no is not None
            else tender.web_tender_no
        ),

        "tender_reference_no": (
            override.tender_reference_no
            if override and override.tender_reference_no is not None
            else tender.tender_reference_no
        ),

        "tender_name": (
            override.tender_name
            if override and override.tender_name is not None
            else tender.tender_name
        ),

        "city": (
            override.city
            if override and override.city is not None
            else tender.city
        ),

        "authority": (
            override.authority
            if override and override.authority is not None
            else tender.authority
        ),

        "organization": (
            override.organization
            if override and override.organization is not None
            else tender.organization
        ),

        "estimated_value": (
            float(override.estimated_value)
            if override and override.estimated_value is not None
            else (
                float(tender.estimated_value)
                if tender.estimated_value is not None
                else None
            )
        ),

        "advertised_date": (
            override.advertised_date
            if override and override.advertised_date is not None
            else tender.advertised_date
        ),

        "closed_date": (
            override.closed_date
            if override and override.closed_date is not None
            else tender.closed_date
        ),

        "source_detail_url": tender.source_detail_url,
        "primary_document_url": tender.primary_document_url,

        "keywords_matched": tender.relevance.matched_keywords,
        "relevance_score": float(
            tender.relevance.keyword_score
        ),
        "matched_capabilities": (
            tender.relevance.matched_capabilities
        ),
        "document": {
            "available": document_available,
            "status": (
                document.download_status
                if document
                else None
            ),
        },
    }


@app.get("/api/tenders/{jazzid}/participation")
def get_tender_participation(
    jazzid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == jazzid)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    if current_user.role.name == "COORDINATOR":
        coordinator = (
            db.query(Coordinator)
            .filter(
                Coordinator.user_id == current_user.id
            )
            .first()
        )

        if coordinator is None:
            raise HTTPException(
                status_code=403,
                detail="Coordinator region is not configured",
            )

        relevance = (
            db.query(TenderRelevance)
            .filter(
                TenderRelevance.tender_jazzid == jazzid
            )
            .first()
        )

        if (
            tender.region_id != coordinator.region_id
            or relevance is None
            or relevance.keyword_score <= 0
        ):
            raise HTTPException(
                status_code=404,
                detail="Tender not found",
            )

    participation = (
        db.query(TenderParticipation)
        .filter(
            TenderParticipation.tender_jazzid == jazzid
        )
        .first()
    )

    if participation is None:
        return {
            "tender_jazzid": jazzid,
            "status": "NOT_REVIEWED",
            "decided_by": None,
            "decided_at": None,
            "delegated_employee_id": None,
            "delegated_employee_name": None,
            "product_ids": None,
        }

    delegated_employee_name = None

    if participation.delegated_employee_id is not None:
        employee = (
            db.query(Employee)
            .filter(
                Employee.id
                == participation.delegated_employee_id
            )
            .first()
        )

        if employee is not None:
            delegated_employee_name = employee.name

    return {
        "tender_jazzid": jazzid,
        "status": participation.status,
        "decided_by": participation.decided_by,
        "decided_at": participation.decided_at,
        "delegated_employee_id": participation.delegated_employee_id,
        "delegated_employee_name": delegated_employee_name,
        "product_ids": participation.product_ids,
    }

@app.put("/api/tenders/{jazzid}/participation")
def update_tender_participation(
    jazzid: int,
    request: TenderParticipationRequest,
    current_user: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        "NOT_REVIEWED",
        "ENGAGING",
        "PARTICIPATED",
        "NOT_PARTICIPATING",
    }

    if request.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid participation status",
        )

    # ---------------------------------------------------------
    # Get coordinator and region
    # ---------------------------------------------------------

    coordinator = (
        db.query(Coordinator)
        .filter(
            Coordinator.user_id == current_user.id
        )
        .first()
    )

    if coordinator is None:
        raise HTTPException(
            status_code=403,
            detail="Coordinator region is not configured",
        )

    # ---------------------------------------------------------
    # Get relevant tender from coordinator's region
    # ---------------------------------------------------------

    tender = (
        db.query(Tender)
        .join(
            TenderSource,
            Tender.source_id == TenderSource.id,
        )
        .join(
            TenderRelevance,
            TenderRelevance.tender_jazzid == Tender.jazzid,
        )
        .filter(
            Tender.jazzid == jazzid,
            Tender.region_id == coordinator.region_id,
            TenderRelevance.keyword_score > 0,
        )
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    # ---------------------------------------------------------
    # Validate ENGAGING requirements and PARTICIPATED transition
    # ---------------------------------------------------------

    employee = None

    if request.status == "ENGAGING":

        # JBC is required
        if request.employee_id is None:
            raise HTTPException(
                status_code=400,
                detail="JBC / Employee is required for participating tenders",
            )

        # At least one product is required
        if not request.product_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one product is required for participating tenders",
            )

        # Validate JBC belongs to coordinator's region
        employee = (
            db.query(Employee)
            .filter(
                Employee.id == request.employee_id,
                Employee.is_active == True,
                Employee.region_id == coordinator.region_id,
            )
            .first()
        )

        if employee is None:
            raise HTTPException(
                status_code=400,
                detail="Employee does not belong to your region or is inactive",
            )

        # -----------------------------------------------------
        # Validate products
        # -----------------------------------------------------

        product_ids = list(dict.fromkeys(request.product_ids))

        products = (
            db.query(Product)
            .filter(
                Product.id.in_(product_ids),
                Product.is_active == True,
            )
            .all()
        )

        if len(products) != len(product_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more selected products are invalid or inactive",
            )

    elif request.status == "PARTICIPATED":
        # Selection data is retained during the ENGAGING -> PARTICIPATED transition.
        product_ids = None

    else:
        # -----------------------------------------------------
        # NOT_PARTICIPATING / NOT_REVIEWED
        # -----------------------------------------------------

        product_ids = None
        request.employee_id = None

    # ---------------------------------------------------------
    # Get or create participation record
    # ---------------------------------------------------------

    participation = (
        db.query(TenderParticipation)
        .filter(
            TenderParticipation.tender_jazzid == jazzid
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    if participation is None:

        if request.status == "PARTICIPATED":
            raise HTTPException(
                status_code=400,
                detail="Only ENGAGING tenders can transition to PARTICIPATED",
            )

        participation = TenderParticipation(
            tender_jazzid=jazzid,
            status=request.status,
            decided_by=current_user.id,
            decided_at=now,
            delegated_employee_id=request.employee_id,
            product_ids=product_ids,
            created_at=now,
            updated_at=now,
        )

        db.add(participation)

    else:

        if request.status == "PARTICIPATED":
            if participation.status != "ENGAGING":
                raise HTTPException(
                    status_code=400,
                    detail="Only ENGAGING tenders can transition to PARTICIPATED",
                )
            if (
                participation.delegated_employee_id is None
                or not participation.product_ids
            ):
                raise HTTPException(
                    status_code=400,
                    detail="ENGAGING tender must have JBC and products before transition",
                )
            request.employee_id = participation.delegated_employee_id
            product_ids = participation.product_ids

        participation.status = request.status
        participation.decided_by = current_user.id
        participation.decided_at = now
        participation.delegated_employee_id = request.employee_id
        participation.product_ids = product_ids
        participation.updated_at = now

    db.commit()
    db.refresh(participation)

    return {
        "message": "Participation updated successfully",
        "tender_jazzid": jazzid,
        "status": participation.status,
        "decided_by": participation.decided_by,
        "decided_at": participation.decided_at,
        "delegated_employee_id": participation.delegated_employee_id,
        "product_ids": participation.product_ids,
    }


@app.get("/api/internal/alerts/pending-participation")
def get_pending_participation_alerts(
    _: bool = Depends(require_alert_service_key),
    db: Session = Depends(get_db),
):
    coordinators = (
        db.query(Coordinator)
        .join(User, Coordinator.user_id == User.id)
        .filter(User.is_active == True)
        .all()
    )

    results = []

    for coordinator in coordinators:
        user = coordinator.user

        tenders = (
            db.query(Tender)
            .join(
                TenderSource,
                Tender.source_id == TenderSource.id,
            )
            .join(
                TenderRelevance,
                TenderRelevance.tender_jazzid
                == Tender.jazzid,
            )
            .outerjoin(
                TenderParticipation,
                TenderParticipation.tender_jazzid
                == Tender.jazzid,
            )
            .filter(
                Tender.region_id
                == coordinator.region_id,
                TenderRelevance.keyword_score > 0,
            )
            .filter(
                (TenderParticipation.id == None)
                |
                (
                    TenderParticipation.status.in_(
                        [
                            "NOT_REVIEWED",
                        ]
                    )
                )
            )
            .order_by(
                Tender.closed_date.asc()
            )
            .all()
        )

        if not tenders:
            continue

        tender_items = []

        for tender in tenders:
            participation = (
                db.query(TenderParticipation)
                .filter(
                    TenderParticipation.tender_jazzid
                    == tender.jazzid
                )
                .first()
            )

            status = (
                participation.status
                if participation
                else "NOT_REVIEWED"
            )

            tender_items.append(
                {
                    "jazzid": tender.jazzid,
                    "web_tender_no": tender.web_tender_no,
                    "tender_reference_no": (
                        tender.tender_reference_no
                    ),
                    "tender_name": tender.tender_name,
                    "source": (
                        tender.source.name
                        if tender.source
                        else None
                    ),
                    "closed_date": tender.closed_date,
                    "status": status,
                }
            )

        results.append(
            {
                "coordinator_id": coordinator.user_id,
                "name": user.name,
                "email": user.email,
                "region_id": coordinator.region_id,
                "pending_count": len(tender_items),
                "tenders": tender_items,
            }
        )

    return {
        "coordinators": results,
        "total_coordinators": len(results),
        "generated_at": datetime.now(timezone.utc),
    }


@app.put("/api/tenders/{jazzid}/participation/delegate")
def delegate_tender(
    jazzid: int,
    request: TenderDelegationRequest,
    current_user: User = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    coordinator = (
        db.query(Coordinator)
        .filter(
            Coordinator.user_id == current_user.id
        )
        .first()
    )

    if coordinator is None:
        raise HTTPException(
            status_code=403,
            detail="Coordinator region is not configured",
        )

    tender = (
        db.query(Tender)
        .join(
            TenderSource,
            Tender.source_id == TenderSource.id,
        )
        .join(
            TenderRelevance,
            TenderRelevance.tender_jazzid == Tender.jazzid,
        )
        .filter(
            Tender.jazzid == jazzid,
            Tender.region_id == coordinator.region_id,
            TenderRelevance.keyword_score > 0,
        )
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    participation = (
        db.query(TenderParticipation)
        .filter(
            TenderParticipation.tender_jazzid == jazzid
        )
        .first()
    )

    if participation is None:
        raise HTTPException(
            status_code=400,
            detail="Tender participation has not been decided",
        )

    if participation.status not in {"ENGAGING", "PARTICIPATED"}:
        raise HTTPException(
            status_code=400,
            detail="Only participating tenders can be delegated",
        )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id == request.employee_id,
            Employee.is_active == True,
            Employee.region_id == coordinator.region_id,
        )
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=400,
            detail="Employee does not belong to your region or is inactive",
        )

    participation.delegated_employee_id = employee.id
    participation.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(participation)

    return {
        "message": "Tender delegated successfully",
        "tender_jazzid": jazzid,
        "delegated_employee_id": participation.delegated_employee_id,
        "delegated_employee_name": employee.name,
    }

def download_tender_document_if_available(
    db: Session,
    tender: Tender,
):
    """
    Download the tender's primary document if a source URL exists
    and the document has not already been downloaded.
    """

    if not tender.primary_document_url:
        return False

    download_lock = get_document_download_lock(
        tender.jazzid
    )

    if not download_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Document download is already in progress.",
        )

    try:
        # Check whether the primary document is already downloaded.
        document = (
            db.query(TenderDocument)
            .filter(
                TenderDocument.tender_jazzid == tender.jazzid,
                TenderDocument.document_type == "PRIMARY",
            )
            .first()
        )

        if document and document.download_status == "DOWNLOADED":
            return False

        # Get the source name from the relationship.
        source_name = tender.source.name

        tender_key = (
            tender.web_tender_no
            or str(tender.jazzid)
        )

        document_name = (
            document.document_name
            if document and document.document_name
            else "tender_document.pdf"
        )

        download_result = download_document(
            tender.primary_document_url,
            source=source_name,
            tender_key=tender_key,
            document_name=document_name,
        )

        if document is None:
            document = TenderDocument(
                tender_jazzid=tender.jazzid,
                document_type="PRIMARY",
                document_name=document_name,
                source_url=tender.primary_document_url,
                download_status=download_result["download_status"],
                local_path=download_result["local_path"],
                file_size=download_result["file_size"],
                downloaded_at=download_result["downloaded_at"],
            )
            db.add(document)

        else:
            document.source_url = tender.primary_document_url
            document.download_status = (
                download_result["download_status"]
            )
            document.local_path = (
                download_result["local_path"]
            )
            document.file_size = (
                download_result["file_size"]
            )
            document.downloaded_at = (
                download_result["downloaded_at"]
            )

        return (
            download_result["download_status"]
            == "DOWNLOADED"
        )

    finally:
        download_lock.release()

@app.put("/api/tenders/{jazzid}")
def update_tender(
    jazzid: int,
    request: TenderUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == jazzid)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    update_data = request.model_dump(
        exclude_unset=True
    )

    # --------------------------------
    # Tender field overrides
    # --------------------------------

    override_fields = {
        "web_tender_no",
        "tender_reference_no",
        "tender_name",
        "city",
        "authority",
        "organization",
        "estimated_value",
        "advertised_date",
        "closed_date",
    }

    override_data = {
        field: value
        for field, value in update_data.items()
        if field in override_fields
    }

    if override_data:
        override = (
            db.query(TenderFieldOverride)
            .filter(
                TenderFieldOverride.tender_jazzid
                == jazzid
            )
            .first()
        )

        if override is None:
            override = TenderFieldOverride(
                tender_jazzid=jazzid,
            )
            db.add(override)

        for field, value in override_data.items():
            setattr(override, field, value)

        override.overridden_by = current_user.id
        override.overridden_at = (
            datetime.now(timezone.utc)
        )

    # --------------------------------
    # Relevance score
    # --------------------------------

    if "relevance_score" in update_data:
        relevance = (
            db.query(TenderRelevance)
            .filter(
                TenderRelevance.tender_jazzid
                == jazzid
            )
            .first()
        )

        if relevance is None:
            raise HTTPException(
                status_code=404,
                detail="Tender relevance record not found",
            )

        old_score = relevance.keyword_score
        new_score = update_data["relevance_score"]

        relevance.keyword_score = new_score

        # If admin makes a previously irrelevant tender relevant,
        # download its primary document if available.
        if old_score <= 0 and new_score > 0:
            download_tender_document_if_available(
                db=db,
                tender=tender,
            )
    db.commit()

    return {
        "message": "Tender updated successfully",
        "jazzid": jazzid,
        "updated_by": current_user.username,
    }


@app.post("/api/tenders/{jazzid}/document/download")
def download_tender_document(
    jazzid: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == jazzid)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    if not tender.primary_document_url:
        raise HTTPException(
            status_code=404,
            detail="Document not available",
        )

    document = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.tender_jazzid == jazzid,
            TenderDocument.document_type == "PRIMARY",
        )
        .first()
    )

    # Prevent downloading an already downloaded document.
    if document and document.download_status == "DOWNLOADED":
        raise HTTPException(
            status_code=409,
            detail="Document has already been downloaded",
        )

    downloaded = download_tender_document_if_available(
        db=db,
        tender=tender,
    )

    if not downloaded:
        raise HTTPException(
            status_code=409,
            detail="Document download was not performed.",
        )

    db.commit()

    return {
        "message": "Tender document downloaded successfully",
        "jazzid": jazzid,
    }

def delete_tender_records(
    jazzids: list[int],
    db: Session,
):
    """
    Delete tenders from the database and remove their
    associated physical document files.
    """

    tenders = (
        db.query(Tender)
        .filter(Tender.jazzid.in_(jazzids))
        .all()
    )

    found_ids = {tender.jazzid for tender in tenders}
    missing_ids = [
        jazzid
        for jazzid in jazzids
        if jazzid not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "One or more tenders were not found.",
                "missing_jazzids": missing_ids,
            },
        )

    # ---------------------------------------------------------
    # Get document paths before deleting the tenders.
    # ---------------------------------------------------------

    document_paths = (
        db.query(TenderDocument.local_path)
        .filter(
            TenderDocument.tender_jazzid.in_(jazzids)
        )
        .all()
    )

    document_paths = [
        row[0]
        for row in document_paths
        if row[0]
    ]

    # ---------------------------------------------------------
    # Delete tenders.
    #
    # Related database records are removed through
    # ON DELETE CASCADE.
    # ---------------------------------------------------------

    for tender in tenders:
        db.delete(tender)

    db.commit()

    # ---------------------------------------------------------
    # Remove physical document files.
    # ---------------------------------------------------------

    documents_root = DOCUMENTS_DIR.resolve()

    deleted_files = []
    failed_files = []

    for local_path in document_paths:
        try:
            file_path = (
                DATA_DIR / local_path
            ).resolve()

            # Safety check:
            # only delete files inside data/documents.
            file_path.relative_to(
                documents_root
            )

            if file_path.is_file():
                file_path.unlink()
                deleted_files.append(local_path)

        except Exception:
            failed_files.append(local_path)

    return {
        "deleted_count": len(tenders),
        "deleted_jazzids": [
            tender.jazzid
            for tender in tenders
        ],
        "documents_deleted": deleted_files,
        "documents_failed": failed_files,
    }


@app.delete("/api/tenders/{jazzid}")
def delete_tender(
    jazzid: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    result = delete_tender_records(
        jazzids=[jazzid],
        db=db,
    )

    return {
        "message": "Tender deleted successfully",
        "jazzid": jazzid,
        "deleted_by": current_user.username,
        **result,
    }


@app.delete("/api/tenders")
def delete_tenders(
    request: BulkTenderDeleteRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # Validate request
    # ---------------------------------------------------------

    jazzids = list(
        dict.fromkeys(request.jazzids)
    )

    if not jazzids:
        raise HTTPException(
            status_code=400,
            detail="At least one tender must be selected.",
        )

    result = delete_tender_records(
        jazzids=jazzids,
        db=db,
    )

    return {
        "message": "Tenders deleted successfully",
        "deleted_by": current_user.username,
        **result,
    }
@app.post("/api/admin/run-scraper")
def run_scraper_now(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
):
    global scraper_running

    if scraper_running:
        raise HTTPException(
            status_code=409,
            detail="Scraper is already running.",
        )

    acquired = scraper_lock.acquire(
        blocking=False
    )

    if not acquired:
        raise HTTPException(
            status_code=409,
            detail="Scraper is already running.",
        )

    scraper_running = True

    def run_scraper_with_lock():
        global scraper_running

        try:
            run_tender_scraper()

        finally:
            scraper_running = False
            scraper_lock.release()

    background_tasks.add_task(
        run_scraper_with_lock
    )

    return {
        "message": "Tender scraper started",
        "started_by": current_user.username,
    }

@app.get("/api/admin/scraper/status")
def get_scraper_status(
    current_user: User = Depends(require_admin),
):
    return {
        "running": scraper_running,
    }


@app.get("/api/admin/scraper/checkpoint")
def get_scraper_checkpoint():
    checkpoint_file = CHECKPOINT_FILE

    if not checkpoint_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Scraper checkpoint file not found.",
        )

    try:
        import json

        with checkpoint_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            checkpoint = json.load(file)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Scraper checkpoint file contains invalid JSON.",
        )

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Unable to read scraper checkpoint file.",
        )

    return checkpoint


@app.get("/api/employees")
def get_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Employee)
        .filter(Employee.is_active == True)
    )

    if current_user.role.name == "COORDINATOR":
        coordinator = (
            db.query(Coordinator)
            .filter(
                Coordinator.user_id == current_user.id
            )
            .first()
        )

        if coordinator is None:
            raise HTTPException(
                status_code=403,
                detail="Coordinator region is not configured",
            )

        query = query.filter(
            Employee.region_id == coordinator.region_id
        )

    employees = (
        query
        .order_by(Employee.name.asc())
        .all()
    )

    return [
        {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "name": employee.name,
            "email": employee.email,
            "region_id": employee.region_id,
            "is_active": employee.is_active,
        }
        for employee in employees
    ]


@app.get("/api/products")
def get_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.id.asc())
        .all()
    )

    return [
        {
            "id": product.id,
            "name": product.name,
        }
        for product in products
    ]


@app.get("/api/tenders/{jazzid}/document")
def view_tender_document(
    jazzid: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == jazzid)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    # Coordinator access control
    if current_user.role.name == "COORDINATOR":
        coordinator = (
            db.query(Coordinator)
            .filter(Coordinator.user_id == current_user.id)
            .first()
        )

        if coordinator is None:
            raise HTTPException(
                status_code=403,
                detail="Coordinator region is not configured",
            )

        relevance = (
            db.query(TenderRelevance)
            .filter(TenderRelevance.tender_jazzid == jazzid)
            .first()
        )

        if (
            tender.region_id != coordinator.region_id
            or relevance is None
            or relevance.keyword_score <= 0
        ):
            raise HTTPException(
                status_code=404,
                detail="Tender not found",
            )

    document = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.tender_jazzid == jazzid,
            TenderDocument.document_type == "PRIMARY",
            TenderDocument.download_status == "DOWNLOADED",
        )
        .first()
    )

    if document is None or not document.local_path:
        raise HTTPException(
            status_code=404,
            detail="Document not available",
        )

    document_path = (DATA_DIR / document.local_path).resolve()
    documents_root = DOCUMENTS_DIR.resolve()

    # Prevent path traversal outside data/documents
    try:
        document_path.relative_to(documents_root)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Document not available",
        )

    if not document_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    media_type, _ = mimetypes.guess_type(document_path.name)

    return FileResponse(
        path=document_path,
        filename=document.document_name or document_path.name,
        media_type=media_type or "application/octet-stream",
    )


# ============================================================
# OVERVIEW FILTER HELPER
# ============================================================



def apply_overview_filters(query, *, region: list[str] | None = None, status: list[str] | None = None, advertised_date_from: str | None = None, advertised_date_to: str | None = None, closing_date_from: str | None = None, closing_date_to: str | None = None, score_min: float | None = None, score_max: float | None = None, product_id: list[int] | None = None):
    """Apply Overview filters using OR within each filter and AND across filters."""

    if region:
        query = query.filter(Region.name.in_(region))

    if status:
        status_conditions = []
        if "NOT_REVIEWED" in status:
            status_conditions.append(or_(TenderParticipation.id.is_(None), TenderParticipation.status == "NOT_REVIEWED"))
        if "ENGAGING" in status:
            status_conditions.append(TenderParticipation.status.in_(["ENGAGING", "PARTICIPATING"]))
        if "PARTICIPATED" in status:
            status_conditions.append(TenderParticipation.status == "PARTICIPATED")
        if "NOT_PARTICIPATING" in status:
            status_conditions.append(TenderParticipation.status == "NOT_PARTICIPATING")
        if status_conditions:
            query = query.filter(or_(*status_conditions))

    if advertised_date_from:
        query = query.filter(Tender.advertised_date >= advertised_date_from)
    if advertised_date_to:
        query = query.filter(Tender.advertised_date <= advertised_date_to)

    if closing_date_from:
        query = query.filter(Tender.closed_date >= closing_date_from)
    if closing_date_to:
        query = query.filter(Tender.closed_date <= closing_date_to)

    if score_min is not None:
        query = query.filter(TenderRelevance.keyword_score >= score_min)
    if score_max is not None:
        query = query.filter(TenderRelevance.keyword_score <= score_max)

    if product_id:
        product_conditions = [func.JSON_CONTAINS(TenderParticipation.product_ids, func.JSON_ARRAY(pid)) == 1 for pid in product_id]
        query = query.filter(or_(*product_conditions))

    return query


# ============================================================
# OVERVIEW ENDPOINT
# ============================================================

@app.get("/api/overview")
def get_overview(
    region: list[str] | None = Query(default=None),
    status: list[str] | None = Query(default=None),
    advertised_date_from: str | None = Query(default=None),
    advertised_date_to: str | None = Query(default=None),
    closing_date_from: str | None = Query(default=None),
    closing_date_to: str | None = Query(default=None),
    score_min: float | None = Query(default=None),
    score_max: float | None = Query(default=None),
    product_id: list[int] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all aggregated data required by the Overview page."""

    allowed_statuses = {"NOT_REVIEWED", "ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING"}
    allowed_regions = {"North1", "North2", "Central", "South"}

    if status:
        invalid_statuses = set(status) - allowed_statuses
        if invalid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid participation status: {sorted(invalid_statuses)}")

    if region:
        invalid_regions = set(region) - allowed_regions
        if invalid_regions:
            raise HTTPException(status_code=400, detail=f"Invalid region: {sorted(invalid_regions)}")

    if score_min is not None and score_min < 0:
        raise HTTPException(status_code=400, detail="score_min cannot be negative")
    if score_max is not None and score_max < 0:
        raise HTTPException(status_code=400, detail="score_max cannot be negative")
    if score_min is not None and score_max is not None and score_min > score_max:
        raise HTTPException(status_code=400, detail="score_min cannot be greater than score_max")
    if product_id and any(pid <= 0 for pid in product_id):
        raise HTTPException(status_code=400, detail="Every product_id must be greater than zero")

    # Coordinator access restrictions
    coordinator_region_id = None
    if current_user.role.name == "COORDINATOR":
        coordinator = db.query(Coordinator).filter(Coordinator.user_id == current_user.id).first()
        if coordinator is None:
            raise HTTPException(status_code=403, detail="Coordinator region is not configured")
        coordinator_region_id = coordinator.region_id

    # Base query
    base_query = (
        db.query(Tender)
        .outerjoin(TenderParticipation, TenderParticipation.tender_jazzid == Tender.jazzid)
        .outerjoin(TenderRelevance, TenderRelevance.tender_jazzid == Tender.jazzid)
        .outerjoin(Region, Region.id == Tender.region_id)
        .join(TenderSource, TenderSource.id == Tender.source_id)
    )

    if coordinator_region_id is not None:
        base_query = base_query.filter(Tender.region_id == coordinator_region_id, TenderRelevance.keyword_score > 0)

    # Apply filters
    base_query = apply_overview_filters(
        base_query,
        region=region,
        status=status,
        advertised_date_from=advertised_date_from,
        advertised_date_to=advertised_date_to,
        closing_date_from=closing_date_from,
        closing_date_to=closing_date_to,
        score_min=score_min,
        score_max=score_max,
        product_id=product_id,
    )

    # Effective participation status
    effective_status = case(
        (or_(TenderParticipation.id.is_(None), TenderParticipation.status == "NOT_REVIEWED"), "NOT_REVIEWED"),
        (TenderParticipation.status == "PARTICIPATING", "ENGAGING"),
        else_=TenderParticipation.status,
    )

    # Summary / KPI
    summary_row = base_query.with_entities(
        func.count(Tender.jazzid).label("total"),
        func.sum(case((effective_status == "NOT_REVIEWED", 1), else_=0)).label("pending"),
        func.sum(case((effective_status == "ENGAGING", 1), else_=0)).label("engaging"),
        func.sum(case((effective_status == "PARTICIPATED", 1), else_=0)).label("participated"),
        func.sum(case((effective_status == "NOT_PARTICIPATING", 1), else_=0)).label("not_participating"),
    ).first()

    total = int(summary_row.total or 0)
    pending = int(summary_row.pending or 0)
    engaging = int(summary_row.engaging or 0)
    participated = int(summary_row.participated or 0)
    not_participating = int(summary_row.not_participating or 0)

    # Date definitions
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    closing_limit = today + timedelta(days=3)

    # Closing within the next 3 days
    closing_soon = base_query.filter(
        Tender.closed_date.isnot(None),
        Tender.closed_date >= today,
        Tender.closed_date <= closing_limit,
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0

    # Activity date: advertised date, falling back to closing date
    activity_date = func.coalesce(Tender.advertised_date, Tender.closed_date)

    # Monthly activity
    monthly_rows = base_query.with_entities(
        func.year(activity_date).label("year"),
        func.month(activity_date).label("month"),
        func.sum(case((effective_status == "ENGAGING", 1), else_=0)).label("engaging"),
        func.sum(case((effective_status == "PARTICIPATED", 1), else_=0)).label("participated"),
        func.sum(case((effective_status == "NOT_PARTICIPATING", 1), else_=0)).label("not_participating"),
        func.sum(case((effective_status == "NOT_REVIEWED", 1), else_=0)).label("not_reviewed"),
        func.count(Tender.jazzid).label("total"),
    ).filter(activity_date.isnot(None)).group_by(
        func.year(activity_date), func.month(activity_date)
    ).order_by(func.year(activity_date), func.month(activity_date)).all()

    monthly_activity = [
        {
            "year": int(row.year),
            "month": int(row.month),
            "engaging": int(row.engaging or 0),
            "participated": int(row.participated or 0),
            "not_participating": int(row.not_participating or 0),
            "not_reviewed": int(row.not_reviewed or 0),
            "total": int(row.total or 0),
        }
        for row in monthly_rows[-12:]
    ]

    # Monthly regional participation
    regional_rows = base_query.with_entities(
        func.year(activity_date).label("year"),
        func.month(activity_date).label("month"),
        Region.name.label("region"),
        effective_status.label("status"),
        func.count(Tender.jazzid).label("count"),
    ).filter(
        activity_date.isnot(None),
        Tender.region_id.isnot(None),
    ).group_by(
        func.year(activity_date), func.month(activity_date), Region.name, effective_status
    ).order_by(
        func.year(activity_date), func.month(activity_date), Region.name
    ).all()

    region_names = ["North1", "North2", "Central", "South"]
    status_names = ["NOT_REVIEWED", "ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING"]
    monthly_regional_map = {}

    for row in regional_rows:
        key = f"{int(row.year):04d}-{int(row.month):02d}"
        if key not in monthly_regional_map:
            monthly_regional_map[key] = {
                "year": int(row.year),
                "month": int(row.month),
                "regions": {
                    name: {s: 0 for s in status_names}
                    for name in region_names
                },
            }
        if row.region in region_names and row.status in status_names:
            monthly_regional_map[key]["regions"][row.region][row.status] = int(row.count or 0)

    monthly_regional = sorted(monthly_regional_map.values(), key=lambda item: (item["year"], item["month"]))[-12:]

    # Leadership metrics
    reviewed = total - pending
    review_rate = round(reviewed / total * 100) if total else 0
    participation_rate = round(participated / reviewed * 100) if reviewed else 0

    high_score_pending = base_query.filter(
        effective_status == "NOT_REVIEWED",
        TenderRelevance.keyword_score >= 70,
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0

    urgent_pending = base_query.filter(
        effective_status == "NOT_REVIEWED",
        Tender.closed_date.isnot(None),
        Tender.closed_date >= today,
        Tender.closed_date <= today + timedelta(days=7),
    ).with_entities(func.count(Tender.jazzid)).scalar() or 0

    # Top 5 portals
    portal_rows = base_query.with_entities(
        TenderSource.name.label("source"),
        func.count(Tender.jazzid).label("count"),
    ).group_by(TenderSource.name).order_by(func.count(Tender.jazzid).desc()).limit(5).all()

    portals = [{"source": row.source, "count": int(row.count or 0)} for row in portal_rows]

    return {
        "summary": {
            "total": total,
            "pending": pending,
            "engaging": engaging,
            "participated": participated,
            "not_participating": not_participating,
            "closing": int(closing_soon),
        },
        "monthly_activity": monthly_activity,
        "monthly_regional": monthly_regional,
        "leadership": {
            "reviewed": reviewed,
            "review_rate": review_rate,
            "participation_rate": participation_rate,
            "high_score_pending": int(high_score_pending),
            "urgent_pending": int(urgent_pending),
            "portals": portals,
        },
    }




@app.post("/api/scraper/import")
def import_scraped_tenders(
    payload: ScraperImportRequest,
):
    """
    Receive raw tender data from locally running
    Punjab/Balochistan scrapers and process it on ECS.
    """

    portal = payload.portal.strip()

    if portal == "Punjab PPRA":

        result = process_local_punjab_tenders(
            tenders=payload.tenders,
        )

        return result

    if portal == "Balochistan PPRA":

        result = process_local_balochistan_tenders(
            tenders=payload.tenders,
        )

        return result

    raise HTTPException(
        status_code=400,
        detail=(
            "Unsupported portal. "
            "Only Punjab PPRA and Balochistan PPRA "
            "are supported for local scraper import."
        ),
    )