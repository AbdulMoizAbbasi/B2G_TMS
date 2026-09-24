import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from tender_scraper.orchestrator_tenderfetch import main as run_tender_scraper
from typing import Literal
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_DIR = Path(__file__).resolve().parent / "data"
TENDERS_FILE = DATA_DIR / "relevant_tenders.json"

class ParticipationRequest(BaseModel):
    participating: bool

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


@app.get("/")
def root():
    return {"message": "JazzWorld B2G Tender Portal API is running"}


@app.get("/api/tenders")
def get_tenders():
    return load_tenders()


@app.get("/api/tenders/{tender_id}")
def get_tender(tender_id: str):
    tenders = load_tenders()

    for tender in tenders:
        if tender.get("id") == tender_id:
            return tender

    raise HTTPException(
        status_code=404,
        detail="Tender not found"
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