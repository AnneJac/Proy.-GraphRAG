import math
from typing import Any

from src.phase_1.graph.connection import get_driver
from src.phase_2.embeddings.embedder import get_embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return -1.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return -1.0

    return dot / (norm1 * norm2)


def _fetch_text_chunks(
    preferred_doc_types: list[str] | None = None,
    preferred_arch_state: str | None = None,
    bank_name: str | None = None,
) -> list[dict[str, Any]]:
    driver = get_driver()

    query = """
    MATCH (c:Chunk)<-[:HAS_CHUNK]-(d:SourceDocument)
    OPTIONAL MATCH (d)-[:BELONGS_TO]->(b:BankEntity)
    WHERE ($preferred_doc_types IS NULL OR size($preferred_doc_types) = 0 OR c.document_type IN $preferred_doc_types)
      AND ($preferred_arch_state IS NULL OR c.architecture_state = $preferred_arch_state)
      AND ($bank_name IS NULL OR b.name = $bank_name)
    RETURN
        c.chunk_id AS chunk_id,
        c.text AS text,
        c.embedding AS embedding,
        c.document_type AS document_type,
        c.architecture_state AS architecture_state,
        d.name AS doc_name,
        d.source_path AS source_path,
        b.name AS bank_name
    """

    with driver.session() as session:
        rows = session.run(
            query,
            preferred_doc_types=preferred_doc_types,
            preferred_arch_state=preferred_arch_state,
            bank_name=bank_name,
        )
        results = [dict(row) for row in rows]

    driver.close()
    return results


def _fetch_multimodal_chunks(
    preferred_doc_types: list[str] | None = None,
    preferred_arch_state: str | None = None,
    bank_name: str | None = None,
) -> list[dict[str, Any]]:
    driver = get_driver()

    query = """
    MATCH (mm:MultiModalChunk)<-[:HAS_MULTIMODAL_CHUNK]-(d:SourceDocument)
    OPTIONAL MATCH (d)-[:BELONGS_TO]->(b:BankEntity)
    WHERE ($preferred_doc_types IS NULL OR size($preferred_doc_types) = 0 OR mm.document_type IN $preferred_doc_types)
      AND ($preferred_arch_state IS NULL OR mm.architecture_state = $preferred_arch_state)
      AND ($bank_name IS NULL OR b.name = $bank_name)
    RETURN
        mm.chunk_id AS chunk_id,
        mm.retrieval_text AS text,
        mm.embedding AS embedding,
        mm.document_type AS document_type,
        mm.architecture_state AS architecture_state,
        mm.modality AS modality,
        mm.page_number AS page_number,
        mm.image_path AS image_path,
        d.name AS doc_name,
        d.source_path AS source_path,
        b.name AS bank_name
    """

    with driver.session() as session:
        rows = session.run(
            query,
            preferred_doc_types=preferred_doc_types,
            preferred_arch_state=preferred_arch_state,
            bank_name=bank_name,
        )
        results = [dict(row) for row in rows]

    driver.close()
    return results


def retrieve_relevant_chunks(
    requirement_text: str,
    preferred_doc_types: list[str] | None = None,
    preferred_arch_state: str | None = None,
    bank_name: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieval textual clásico.
    """
    query_embedding = get_embedding(requirement_text)
    if query_embedding is None:
        return []

    candidates = _fetch_text_chunks(
        preferred_doc_types=preferred_doc_types,
        preferred_arch_state=preferred_arch_state,
        bank_name=bank_name,
    )

    scored = []
    for chunk in candidates:
        embedding = chunk.get("embedding")
        if not embedding:
            continue

        score = cosine_similarity(query_embedding, embedding)
        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk.get("text", ""),
                "score": score,
                "document_type": chunk.get("document_type"),
                "architecture_state": chunk.get("architecture_state"),
                "doc_name": chunk.get("doc_name"),
                "source_path": chunk.get("source_path"),
                "bank_name": chunk.get("bank_name"),
                "retrieval_kind": "text",
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def retrieve_relevant_multimodal_chunks(
    requirement_text: str,
    preferred_doc_types: list[str] | None = None,
    preferred_arch_state: str | None = None,
    bank_name: str | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieval multimodal basado en embeddings de retrieval_text.
    """
    query_embedding = get_embedding(requirement_text)
    if query_embedding is None:
        return []

    candidates = _fetch_multimodal_chunks(
        preferred_doc_types=preferred_doc_types,
        preferred_arch_state=preferred_arch_state,
        bank_name=bank_name,
    )

    scored = []
    for chunk in candidates:
        embedding = chunk.get("embedding")
        if not embedding:
            continue

        score = cosine_similarity(query_embedding, embedding)
        scored.append(
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk.get("text", ""),
                "score": score,
                "document_type": chunk.get("document_type"),
                "architecture_state": chunk.get("architecture_state"),
                "modality": chunk.get("modality", "hybrid"),
                "page_number": chunk.get("page_number"),
                "image_path": chunk.get("image_path"),
                "doc_name": chunk.get("doc_name"),
                "source_path": chunk.get("source_path"),
                "bank_name": chunk.get("bank_name"),
                "retrieval_kind": "multimodal",
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def retrieve_hybrid_context(
    requirement_text: str,
    preferred_doc_types: list[str] | None = None,
    preferred_arch_state: str | None = None,
    bank_name: str | None = None,
    top_k_text: int = 5,
    top_k_multimodal: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """
    Devuelve ambos tipos de resultados separados para que el workspace
    pueda enlazarlos de forma explícita.
    """
    text_chunks = retrieve_relevant_chunks(
        requirement_text=requirement_text,
        preferred_doc_types=preferred_doc_types,
        preferred_arch_state=preferred_arch_state,
        bank_name=bank_name,
        top_k=top_k_text,
    )

    multimodal_chunks = retrieve_relevant_multimodal_chunks(
        requirement_text=requirement_text,
        preferred_doc_types=preferred_doc_types,
        preferred_arch_state=preferred_arch_state,
        bank_name=bank_name,
        top_k=top_k_multimodal,
    )

    return {
        "text_chunks": text_chunks,
        "multimodal_chunks": multimodal_chunks,
    }


def get_bank_context(bank_name: str) -> dict[str, Any]:
    driver = get_driver()

    query = """
    MATCH (b:BankEntity {name: $bank_name})
    OPTIONAL MATCH (b)-[:HAS_PROFILE]->(bp:BankProfile)
    RETURN 
        b.name AS name,
        b.country AS country,
        b.tier AS tier,
        bp.architecture_style AS architecture_style,
        bp.core_banking_system AS core_banking_system,
        bp.data_platform AS data_platform
    """

    with driver.session() as session:
        result = session.run(query, bank_name=bank_name)
        row = result.single()

    driver.close()
    return dict(row) if row else {}