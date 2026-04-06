from pydantic import BaseModel
from typing import List, Optional


class WorkspaceBuildRequest(BaseModel):
    workspace_id: str
    requirement_text: str
    preferred_doc_types: List[str] = []
    preferred_arch_state: Optional[str] = None


class WorkspaceChunkResponse(BaseModel):
    chunk_id: str
    document_type: str
    architecture_state: Optional[str] = None
    score: float
    text: str


class WorkspaceBuildResponse(BaseModel):
    workspace_id: str
    message: str
    chunks: List[WorkspaceChunkResponse]


class ProposalRequest(BaseModel):
    workspace_id: str


class ProposalResponse(BaseModel):
    workspace_id: str
    proposal: str


class ExportPdfRequest(BaseModel):
    workspace_id: str
    proposal: str


class ExportPdfResponse(BaseModel):
    workspace_id: str
    url: str