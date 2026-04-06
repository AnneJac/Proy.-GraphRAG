from pathlib import Path
from typing import List

from scripts.phase_2.build_workspace import build_workspace
from src.phase_2.orchestration.proposal_generator import generate_workspace_proposal
from src.phase_1.graph.connection import get_driver


def get_workspace_chunks(workspace_id: str) -> List[dict]:
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (w:Workspace {workspace_id: $workspace_id})-[r:RETRIEVED_CHUNK]->(c:Chunk)
            RETURN c.chunk_id AS chunk_id,
                   c.text AS text,
                   r.score AS score,
                   r.document_type AS document_type,
                   r.architecture_state AS architecture_state
            ORDER BY r.score DESC
            LIMIT 8
            """,
            workspace_id=workspace_id,
        )
        rows = [dict(row) for row in result]

    driver.close()
    return rows


def build_workspace_service(
    workspace_id: str,
    requirement_text: str,
    preferred_doc_types: list[str],
    preferred_arch_state: str | None,
) -> dict:
    build_workspace(
        requirement_text=requirement_text,
        workspace_id=workspace_id,
        preferred_doc_types=preferred_doc_types,
        preferred_arch_state=preferred_arch_state,
    )

    chunks = get_workspace_chunks(workspace_id)

    return {
        "workspace_id": workspace_id,
        "message": f"Workspace {workspace_id} construido correctamente.",
        "chunks": chunks,
    }


def generate_proposal_service(workspace_id: str) -> dict:
    proposal = generate_workspace_proposal(workspace_id)

    return {
        "workspace_id": workspace_id,
        "proposal": proposal,
    }


def export_pdf_service(workspace_id: str, proposal: str) -> dict:
    output_dir = Path("output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Por ahora guardamos un TXT para validar el flujo.
    # Después lo reemplazamos por PDF real.
    file_path = output_dir / f"{workspace_id}_proposal.txt"
    file_path.write_text(proposal, encoding="utf-8")

    return {
        "workspace_id": workspace_id,
        "url": f"/downloads/{file_path.name}",
    }