import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import text
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models.tender import Tender
from database.models.tender_document import TenderDocument
from database.models.user import User
from auth import verify_password, create_access_token

import jwt

from auth import decode_access_token


from tender_scraper.orchestrator_tenderfetch import (
    main as run_tender_scraper
)

from project_updates.project_service import (
    get_all_projects,
    get_project_by_id,
)

from project_updates.project_news import (
    get_news_for_project,
    refresh_project_news,
)

from evaluation_scraper.storage import (
    load_evaluation_reports,
    get_evaluation,
)

from evaluation_scraper.orchestrator_evaluationfetch import (
    process_all_relevant_tenders,
)

app = FastAPI(title="JazzWorld B2G Tender Portal")

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






DATA_DIR = Path(__file__).resolve().parent / "data"
TENDERS_FILE = DATA_DIR / "relevant_tenders.json"

class ParticipationRequest(BaseModel):
    participating: bool

class LoginRequest(BaseModel):
    username: str
    password: str

class ProgressRequest(BaseModel):
    stage: Literal[
        "Participation",
        "Bid Preparation",
        "Bid Submitted"
    ]
class ResultRequest(BaseModel):
    result: Literal[
        "Win",
        "Lost",
        "Result Not Announced"
    ]

def load_tenders():
    with open(TENDERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)




@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
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
    return {"message": "JazzWorld B2G Tender Portal API is running"}


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

@app.get("/api/health/db")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).scalar()

    return {
        "status": "ok",
        "database": result == 1,
    }

@app.get("/api/tenders")
def get_tenders(db: Session = Depends(get_db)):
    tenders = (
        db.query(Tender)
        .order_by(Tender.jazzid.desc())
        .all()
    )

    return [
        {
            "jazzid": tender.jazzid,
            "source_id": tender.source_id,
            "source": (
                tender.source.name
                if tender.source
                else None
            ),
            "region": (
                tender.source.region.name
                if tender.source and tender.source.region
                else None
            ),
            "web_tender_no": tender.web_tender_no,
            "tender_reference_no": tender.tender_reference_no,
            "tender_name": tender.tender_name,
            "city": tender.city,
            "authority": tender.authority,
            "organization": tender.organization,
            "estimated_value": (
                float(tender.estimated_value)
                if tender.estimated_value is not None
                else None
            ),
            "advertised_date": tender.advertised_date,
            "closed_date": tender.closed_date,
            "source_detail_url": tender.source_detail_url,
            "primary_document_url": tender.primary_document_url,

            "keywords_matched": (
                tender.relevance.matched_keywords
                if tender.relevance
                else []
            ),
            "relevance_score": (
                float(tender.relevance.keyword_score)
                if tender.relevance
                else 0.0
            ),
            "matched_capabilities": (
                tender.relevance.matched_capabilities
                if tender.relevance
                else []
            ),
        }
        for tender in tenders
    ]


@app.get("/api/tenders/{tender_id}")
def get_tender(
    tender_id: int,
    db: Session = Depends(get_db),
):
    tender = (
        db.query(Tender)
        .filter(Tender.jazzid == tender_id)
        .first()
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found",
        )

    return {
        "jazzid": tender.jazzid,
        "source_id": tender.source_id,
        "source": (
            tender.source.name
            if tender.source
            else None
        ),
        "region": (
            tender.source.region.name
            if tender.source and tender.source.region
            else None
        ),
        "web_tender_no": tender.web_tender_no,
        "tender_reference_no": tender.tender_reference_no,
        "tender_name": tender.tender_name,
        "city": tender.city,
        "authority": tender.authority,
        "organization": tender.organization,
        "estimated_value": (
            float(tender.estimated_value)
            if tender.estimated_value is not None
            else None
        ),
        "estimated_value_source": tender.estimated_value_source,
        "advertised_date": tender.advertised_date,
        "closed_date": tender.closed_date,
        "source_detail_url": tender.source_detail_url,
        "primary_document_url": tender.primary_document_url,

        "keywords_matched": (
            tender.relevance.matched_keywords
            if tender.relevance
            else []
        ),
        "relevance_score": (
            float(tender.relevance.keyword_score)
            if tender.relevance
            else 0.0
        ),
        "matched_capabilities": (
            tender.relevance.matched_capabilities
            if tender.relevance
            else []
        ),
        "raw_data": tender.raw_data,
        "documents": [
            {
                "id": document.id,
                "document_type": document.document_type,
                "document_name": document.document_name,
                "source_url": document.source_url,
                "local_path": document.local_path,
                "download_status": document.download_status,
                "file_size": document.file_size,
                "downloaded_at": document.downloaded_at,
            }
            for document in tender.documents
        ],             
    }


@app.get("/api/tenders/{tender_id}/documents/{document_id}")
def download_tender_document(
    tender_id: int,
    document_id: int,
    db: Session = Depends(get_db),
):
    document = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.id == document_id,
            TenderDocument.tender_jazzid == tender_id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document.download_status != "DOWNLOADED":
        raise HTTPException(
            status_code=404,
            detail="Document is not available",
        )

    if not document.local_path:
        raise HTTPException(
            status_code=404,
            detail="Local document path not available",
        )

    file_path = Path(__file__).resolve().parent / document.local_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    filename = document.document_name or "tender_document.pdf"

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )
        
PROGRESS_FILE = DATA_DIR / "tender_progress.json"


def load_progress():
    with open(PROGRESS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as file:
        json.dump(progress, file, indent=2)



@app.get("/api/tenders/{tender_id}/progress")
def get_tender_progress(tender_id: str):
    tenders = load_tenders()

    tender = next(
        (
            tender
            for tender in tenders
            if tender.get("id") == tender_id
            or tender.get("web_tender_no") == tender_id
        ),
        None
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found"
        )

    progress = load_progress()

    return progress.get(
        tender["id"],
        {
            "participating": False,
            "stage": None,
            "result": None
        }
    )


@app.post("/api/scraper/tenders/run")
def run_tenders_scraper():
    results = run_tender_scraper()

    return {
        "status": "completed",
        "results": results
    }


@app.patch("/api/tenders/{tender_id}/participation")
def update_participation(
    tender_id: str,
    request: ParticipationRequest
):
    tenders = load_tenders()

    tender = next(
        (
            tender
            for tender in tenders
            if tender.get("id") == tender_id
            or tender.get("web_tender_no") == tender_id
        ),
        None
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found"
        )

    progress = load_progress()

    existing = progress.get(tender["id"], {})

    existing["participating"] = request.participating

    if request.participating:
        if existing.get("stage") is None:
            existing["stage"] = "Participation"
    else:
        existing["stage"] = None
        existing["result"] = None

    progress[tender["id"]] = existing

    save_progress(progress)

    return {
        "tender_id": tender["id"],
        "participating": existing["participating"],
        "stage": existing.get("stage"),
        "result": existing.get("result")
    }


@app.patch("/api/tenders/{tender_id}/progress")
def update_tender_progress(
    tender_id: str,
    request: ProgressRequest
):
    tenders = load_tenders()

    tender = next(
        (
            tender
            for tender in tenders
            if tender.get("id") == tender_id
            or tender.get("web_tender_no") == tender_id
        ),
        None
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found"
        )

    progress = load_progress()

    tender_key = tender["id"]

    existing = progress.get(
        tender_key,
        {
            "participating": False,
            "stage": None,
            "result": None
        }
    )

    if not existing.get("participating"):
        raise HTTPException(
            status_code=400,
            detail="Tender is not marked as participating"
        )

    existing["stage"] = request.stage

    progress[tender_key] = existing

    save_progress(progress)

    return {
        "tender_id": tender_key,
        "participating": existing["participating"],
        "stage": existing["stage"],
        "result": existing.get("result")
    }


@app.patch("/api/tenders/{tender_id}/result")
def update_tender_result(
    tender_id: str,
    request: ResultRequest
):
    tenders = load_tenders()

    tender = next(
        (
            tender
            for tender in tenders
            if tender.get("id") == tender_id
            or tender.get("web_tender_no") == tender_id
        ),
        None
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found"
        )

    progress = load_progress()

    tender_key = tender["id"]

    existing = progress.get(
        tender_key,
        {
            "participating": False,
            "stage": None,
            "result": None
        }
    )

    if not existing.get("participating"):
        raise HTTPException(
            status_code=400,
            detail="Tender is not marked as participating"
        )

    existing["result"] = request.result

    if request.result == "Result Not Announced":
        existing["stage"] = "Bid Submitted"
    else:
        existing["stage"] = "Result Announced"

    progress[tender_key] = existing

    save_progress(progress)

    return {
        "tender_id": tender_key,
        "participating": existing["participating"],
        "stage": existing["stage"],
        "result": existing["result"]
    }

@app.delete("/api/tenders/{tender_id}")
def delete_tender(tender_id: str):
    tenders = load_tenders()

    tender = next(
        (
            tender
            for tender in tenders
            if tender.get("id") == tender_id
            or tender.get("web_tender_no") == tender_id
        ),
        None
    )

    if tender is None:
        raise HTTPException(
            status_code=404,
            detail="Tender not found"
        )

    tender_key = tender["id"]

    # Remove tender from master tender data
    updated_tenders = [
        item
        for item in tenders
        if item.get("id") != tender_key
    ]

    with open(TENDERS_FILE, "w", encoding="utf-8") as file:
        json.dump(updated_tenders, file, indent=2)

    # Remove associated progress data
    progress = load_progress()

    if tender_key in progress:
        del progress[tender_key]
        save_progress(progress)

    return {
        "status": "deleted",
        "tender_id": tender_key,
        "web_tender_no": tender.get("web_tender_no")
    }


# ============================================================
# PROJECT UPDATES APIs
# ============================================================

@app.get("/api/projects")
def get_projects():
    try:
        return get_all_projects()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    try:
        project = get_project_by_id(project_id)

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        project["news"] = get_news_for_project(
            project_id
        )

        return project

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/api/projects/{project_id}/news/refresh")
def refresh_project_news_api(project_id: str):
    try:
        project = get_project_by_id(project_id)

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        project_name = project.get(
            "Project / Scheme Name"
        )

        if not project_name:
            raise HTTPException(
                status_code=400,
                detail="Project name not found"
            )

        result = refresh_project_news(
            project_id=project_id,
            project_name=project_name
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
    

@app.get("/api/evaluations")
def get_evaluations():
    try:
        evaluations = load_evaluation_reports()

        relevant_tenders_file = (
            Path(__file__).resolve().parent
            / "data"
            / "relevant_tenders.json"
        )

        tender_lookup = {}

        if relevant_tenders_file.exists():
            with open(
                relevant_tenders_file,
                "r",
                encoding="utf-8"
            ) as f:
                relevant_tenders = json.load(f)

            for tender in relevant_tenders:
                tender_no = (
                    tender.get("web_tender_no")
                    or tender.get("TSENumber")
                    or tender.get("tender_number")
                )

                if tender_no:
                    tender_lookup[tender_no] = tender

        enriched_evaluations = []

        for evaluation in evaluations:
            evaluation_copy = dict(evaluation)

            scraped_data = evaluation.get(
                "scraped_data",
                {}
            )

            tender_no = scraped_data.get(
                "tender_no"
            )

            tender_data = tender_lookup.get(
                tender_no
            )

            evaluation_copy["tender_data"] = (
                tender_data
                if tender_data
                else None
            )

            enriched_evaluations.append(
                evaluation_copy
            )

        return {
            "value": enriched_evaluations,
            "Count": len(enriched_evaluations)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/evaluations/{tender_no}")
def get_evaluation_by_tender(tender_no: str):
    try:
        evaluations = load_evaluation_reports()

        # Find all evaluation reports belonging
        # to this tender.
        tender_evaluations = []

        for evaluation in evaluations:
            scraped_data = (
                evaluation.get("scraped_data", {})
            )

            evaluation_tender_no = (
                scraped_data.get("tender_no")
            )

            if evaluation_tender_no == tender_no:
                tender_evaluations.append(
                    evaluation
                )

        if not tender_evaluations:
            raise HTTPException(
                status_code=404,
                detail="No evaluation reports found for this tender"
            )

        # --------------------------------------------------
        # Find original tender from relevant_tenders.json
        # --------------------------------------------------

        relevant_tenders_file = (
            Path(__file__).resolve().parent
            / "data"
            / "relevant_tenders.json"
        )

        with open(
            relevant_tenders_file,
            "r",
            encoding="utf-8"
        ) as f:
            relevant_tenders = json.load(f)

        # Handle both possible JSON structures
        if isinstance(
            relevant_tenders,
            dict
        ):
            if isinstance(
                relevant_tenders.get("value"),
                list
            ):
                relevant_tenders = (
                    relevant_tenders["value"]
                )
            else:
                relevant_tenders = list(
                    relevant_tenders.values()
                )

        tender_data = None

        for tender in relevant_tenders:
            candidate_no = (
                tender.get("web_tender_no")
                or tender.get("TSENumber")
                or tender.get("tender_number")
            )

            if candidate_no == tender_no:
                tender_data = tender
                break

        # --------------------------------------------------
        # Return tender + ALL evaluation reports
        # --------------------------------------------------

        return {
            "tender_no": tender_no,
            "tender_data": tender_data,
            "evaluations": tender_evaluations,
            "evaluation_count": len(
                tender_evaluations
            ),
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@app.get("/api/evaluations/{evaluation_id}/pdf")
def get_evaluation_pdf(evaluation_id: str):
    try:
        evaluation = get_evaluation(
            evaluation_id
        )

        if evaluation is None:
            raise HTTPException(
                status_code=404,
                detail="Evaluation not found"
            )

        pdf_path = evaluation.get(
            "pdf_path"
        )

        if not pdf_path:
            raise HTTPException(
                status_code=404,
                detail="PDF not available for this evaluation"
            )

        pdf_file = (
            Path(__file__).resolve().parent
            / "data"
            / "evaluation_pdfs"
            / pdf_path
        )

        if not pdf_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Evaluation PDF file not found"
            )

        return FileResponse(
            path=str(pdf_file),
            media_type="application/pdf",
            filename=pdf_file.name,
            headers={
                "Content-Disposition":
                    "inline"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/api/evaluations/fetch")
def fetch_evaluations():
    try:
        results = process_all_relevant_tenders()

        return {
            "status": "completed",
            "results": results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )