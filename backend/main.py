from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from sqlalchemy.orm import Session

import jwt

from database.connection import SessionLocal
from database.models.user import User
from database.models.coordinator import Coordinator
from database.models.tender_source import TenderSource
from database.models.tender_relevance import TenderRelevance
from database.models.tender import Tender
from database.models.tender_field_override import TenderFieldOverride

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import BackgroundTasks
from tender_scraper.orchestrator_tenderfetch import main as run_tender_scraper

from auth import (
    verify_password,
    create_access_token,
    decode_access_token,
)


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


@app.get("/")
def root():
    return {
        "message": "JazzWorld B2G Tender Portal API is running"
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
            TenderSource.region_id == coordinator.region_id,
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
            "region": tender.source.region.name,

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

    override = (
        db.query(TenderFieldOverride)
        .filter(TenderFieldOverride.tender_jazzid == jazzid)
        .first()
    )

    if override is None:
        override = TenderFieldOverride(
            tender_jazzid=jazzid,
        )
        db.add(override)

    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(override, field, value)

    override.overridden_by = current_user.id
    override.overridden_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(override)

    return {
        "message": "Tender updated successfully",
        "jazzid": jazzid,
        "overridden_by": current_user.username,
        "overridden_at": override.overridden_at,
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

    db.delete(tender)
    db.commit()

    return {
        "message": "Tender deleted successfully",
        "jazzid": jazzid,
        "deleted_by": current_user.username,
    }


@app.post("/api/admin/run-scraper")
def run_scraper_now(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
):
    background_tasks.add_task(run_tender_scraper)

    return {
        "message": "Tender scraper started",
        "started_by": current_user.username,
    }