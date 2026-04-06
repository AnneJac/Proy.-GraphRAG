import typer

from src.phase_2.retrieval.retrieval import retrieve_hybrid_context, get_bank_context
from src.phase_2.workspace.workspace_loader import (
    attach_chunks_to_workspace,
    attach_multimodal_chunks_to_workspace,
    create_workspace,
)

app = typer.Typer(help="Construcción de workspace con retrieval híbrido.")


def _parse_doc_types(value: str | None) -> list[str]:
    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


@app.command()
def build_workspace(
    workspace_id: str = typer.Option(..., help="ID único del workspace."),
    requirement_text: str = typer.Option(..., help="Requerimiento o necesidad de negocio."),
    bank_name: str = typer.Option(None, help="Nombre del banco para filtrar contexto."),
    preferred_doc_types: str = typer.Option(
        "",
        help="Lista separada por comas. Ej: RFP,TECHNICAL_ANNEX,MEETING_MINUTES",
    ),
    preferred_arch_state: str = typer.Option(
        None,
        help="Filtrar por estado de arquitectura. Ej: AS-IS, TO-BE",
    ),
    top_k_text: int = typer.Option(5, help="Top K para chunks textuales."),
    top_k_multimodal: int = typer.Option(3, help="Top K para chunks multimodales."),
):
    parsed_doc_types = _parse_doc_types(preferred_doc_types)

    bank_context = {}
    if bank_name:
        bank_context = get_bank_context(bank_name)
        print(f"🏦 Contexto de banco cargado: {bank_context.get('name', bank_name)}")

    create_workspace(
        workspace_id=workspace_id,
        requirement_text=requirement_text,
        preferred_doc_types=parsed_doc_types,
        preferred_arch_state=preferred_arch_state,
    )

    retrieval_result = retrieve_hybrid_context(
        requirement_text=requirement_text,
        preferred_doc_types=parsed_doc_types,
        preferred_arch_state=preferred_arch_state,
        bank_name=bank_name,
        top_k_text=top_k_text,
        top_k_multimodal=top_k_multimodal,
    )

    text_chunks = retrieval_result["text_chunks"]
    multimodal_chunks = retrieval_result["multimodal_chunks"]

    if text_chunks:
        attach_chunks_to_workspace(workspace_id, text_chunks)

    if multimodal_chunks:
        attach_multimodal_chunks_to_workspace(workspace_id, multimodal_chunks)

    print(f"✅ Workspace creado/actualizado: {workspace_id}")
    if bank_name:
        print(f"✅ Banco filtrado: {bank_name}")
    print(f"✅ Chunks textuales vinculados: {len(text_chunks)}")
    print(f"✅ Chunks multimodales vinculados: {len(multimodal_chunks)}")

    if text_chunks:
        print("\n--- Top text chunks ---")
        for idx, chunk in enumerate(text_chunks, start=1):
            print(
                f"{idx}. {chunk['chunk_id']} | score={chunk['score']:.4f} | "
                f"doc_type={chunk.get('document_type')} | arch={chunk.get('architecture_state')} | "
                f"bank={chunk.get('bank_name')}"
            )

    if multimodal_chunks:
        print("\n--- Top multimodal chunks ---")
        for idx, chunk in enumerate(multimodal_chunks, start=1):
            print(
                f"{idx}. {chunk['chunk_id']} | score={chunk['score']:.4f} | "
                f"modality={chunk.get('modality')} | page={chunk.get('page_number')} | "
                f"doc_type={chunk.get('document_type')} | arch={chunk.get('architecture_state')} | "
                f"bank={chunk.get('bank_name')}"
            )


if __name__ == "__main__":
    app()