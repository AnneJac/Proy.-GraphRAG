from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.schemas import (
    WorkspaceBuildRequest,
    WorkspaceBuildResponse,
    ProposalRequest,
    ProposalResponse,
    ExportPdfRequest,
    ExportPdfResponse,
)
from api.services import (
    build_workspace_service,
    generate_proposal_service,
    export_pdf_service,
)

app = FastAPI(title="GraphRAG Thesis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reports_dir = Path("output/reports")
reports_dir.mkdir(parents=True, exist_ok=True)

app.mount("/downloads", StaticFiles(directory=str(reports_dir)), name="downloads")


@app.get("/")
def root():
    return {"message": "GraphRAG Thesis API running"}


@app.post("/workspace/build", response_model=WorkspaceBuildResponse)
def build_workspace_endpoint(payload: WorkspaceBuildRequest):
    return build_workspace_service(
        workspace_id=payload.workspace_id,
        requirement_text=payload.requirement_text,
        preferred_doc_types=payload.preferred_doc_types,
        preferred_arch_state=payload.preferred_arch_state,
    )


@app.post("/proposal/generate", response_model=ProposalResponse)
def generate_proposal_endpoint(payload: ProposalRequest):
    return generate_proposal_service(payload.workspace_id)


@app.post("/report/export-pdf", response_model=ExportPdfResponse)
def export_pdf_endpoint(payload: ExportPdfRequest):
    return export_pdf_service(
        workspace_id=payload.workspace_id,
        proposal=payload.proposal,
    )