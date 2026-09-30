from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import threading
from fastapi import Header
from pathlib import Path

from sqlalchemy.orm import Session

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

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from fastapi import BackgroundTasks
from tender_scraper.orchestrator_tenderfetch import main as run_tender_scraper

from auth import (
    verify_password,
    create_access_token,
    decode_access_token,
)

# ============================================================
# SCRAPER EXECUTION STATE
# ============================================================

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
        "UNDER_REVIEW",
        "PARTICIPATING",
        "NOT_PARTICIPATING",
    ]
    employee_id: int | None = None
    product_ids: list[int] | None = None

class TenderDelegationRequest(BaseModel):
    employee_id: int


class TenderRegionUpdateRequest(BaseModel):
    region_id: int


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Tender)
        .join(
            TenderSource,
            Tender.source_id == TenderSource.id,
        )
        .join(
            TenderRelevance,
            TenderRelevance.tender_jazzid == Tender.jazzid,
        )
        .outerjoin(
            TenderFieldOverride,
            TenderFieldOverride.tender_jazzid == Tender.jazzid,
        )
    )

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

        query = query.filter(
            Tender.region_id == coordinator.region_id,
            TenderRelevance.keyword_score > 0,
        )

    tenders = query.order_by(Tender.jazzid.desc()).all()

    result = []

    for tender in tenders:
        override = tender.field_override

        result.append({
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
            "relevance_score": float(tender.relevance.keyword_score),
            "matched_capabilities": tender.relevance.matched_capabilities,
        })

    return result


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
        .join(
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
        "UNDER_REVIEW",
        "PARTICIPATING",
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
    # Validate PARTICIPATING requirements
    # ---------------------------------------------------------

    employee = None

    if request.status == "PARTICIPATING":

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
                TenderSource.region_id
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
                            "UNDER_REVIEW",
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

    if participation.status != "PARTICIPATING":
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

        relevance.keyword_score = (
            update_data["relevance_score"]
        )

    db.commit()

    return {
        "message": "Tender updated successfully",
        "jazzid": jazzid,
        "updated_by": current_user.username,
    }



@app.delete("/api/tenders/{jazzid}")
def delete_tender(
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

    # Get document paths before deleting the tender.
    document_paths = (
        db.query(TenderDocument.local_path)
        .filter(TenderDocument.tender_jazzid == jazzid)
        .all()
    )

    document_paths = [
        row[0]
        for row in document_paths
        if row[0]
    ]

    # Delete tender.
    # Related database records are removed through ON DELETE CASCADE.
    db.delete(tender)
    db.commit()

    # Remove physical document files.
    backend_root = Path(__file__).resolve().parent
    documents_root = (backend_root / "documents").resolve()

    deleted_files = []
    failed_files = []

    for local_path in document_paths:
        try:
            file_path = (backend_root / local_path).resolve()

            # Safety check: only delete files inside backend/documents.
            file_path.relative_to(documents_root)

            if file_path.is_file():
                file_path.unlink()
                deleted_files.append(local_path)

        except Exception:
            failed_files.append(local_path)

    return {
        "message": "Tender deleted successfully",
        "jazzid": jazzid,
        "deleted_by": current_user.username,
        "documents_deleted": deleted_files,
        "documents_failed": failed_files,
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