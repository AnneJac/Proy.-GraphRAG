from typing import Any

from src.phase_1.graph.connection import get_driver


def save_multimodal_chunks(
    doc_name: str,
    source_path: str,
    file_hash: str,
    multimodal_chunks: list[dict[str, Any]],
) -> None:
    """
    Guarda:
    - Page
    - MultiModalChunk
    - relaciones con SourceDocument
    """
    if not multimodal_chunks:
        return

    driver = get_driver()

    query = """
    MERGE (d:SourceDocument {file_hash: $file_hash})
    SET d.name = $doc_name,
        d.source_path = $source_path

    WITH d
    UNWIND $chunks AS chunk

    MERGE (p:Page {page_id: chunk.page_id})
    SET p.page_number = chunk.page_number,
        p.source_path = chunk.source_path,
        p.image_path = chunk.image_path

    MERGE (d)-[:HAS_PAGE]->(p)

    MERGE (mm:MultiModalChunk {chunk_id: chunk.chunk_id})
    SET mm.chunk_hash = chunk.chunk_hash,
        mm.page_number = chunk.page_number,
        mm.source_path = chunk.source_path,
        mm.image_path = chunk.image_path,
        mm.modality = chunk.modality,
        mm.chunk_type = chunk.chunk_type,
        mm.raw_text = chunk.raw_text,
        mm.visual_summary = chunk.visual_summary,
        mm.table_content = chunk.table_content,
        mm.llm_summary = chunk.llm_summary,
        mm.retrieval_text = chunk.retrieval_text,
        mm.embedding = chunk.embedding,
        mm.document_type = chunk.document_type,
        mm.architecture_state = chunk.architecture_state,
        mm.table_detected = chunk.table_detected,
        mm.diagram_detected = chunk.diagram_detected,
        mm.technical_components_json = chunk.technical_components_json,
        mm.business_terms_json = chunk.business_terms_json,
        mm.key_entities_json = chunk.key_entities_json,
        mm.visual_elements_json = chunk.visual_elements_json,
        mm.confidence = chunk.confidence

    MERGE (d)-[:HAS_MULTIMODAL_CHUNK]->(mm)
    MERGE (mm)-[:FROM_PAGE]->(p)
    """

    with driver.session() as session:
        session.run(
            query,
            doc_name=doc_name,
            source_path=source_path,
            file_hash=file_hash,
            chunks=multimodal_chunks,
        )

    driver.close()