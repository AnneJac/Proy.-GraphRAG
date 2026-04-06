from src.phase_1.graph.connection import get_driver


def create_workspace(
    workspace_id: str,
    requirement_text: str,
    preferred_doc_types: list[str],
    preferred_arch_state: str | None,
):
    driver = get_driver()

    with driver.session() as session:
        session.run(
            """
            MERGE (w:Workspace {workspace_id: $workspace_id})
            SET w.requirement_text = $requirement_text,
                w.preferred_doc_types = $preferred_doc_types,
                w.preferred_arch_state = $preferred_arch_state
            """,
            workspace_id=workspace_id,
            requirement_text=requirement_text,
            preferred_doc_types=preferred_doc_types,
            preferred_arch_state=preferred_arch_state,
        )

    driver.close()


def attach_chunks_to_workspace(workspace_id: str, chunks: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        for chunk in chunks:
            props = {
                "score": chunk["score"],
                "document_type": chunk["document_type"],
            }

            if chunk.get("architecture_state") is not None:
                props["architecture_state"] = chunk["architecture_state"]

            session.run(
                """
                MERGE (w:Workspace {workspace_id: $workspace_id})
                MATCH (c:Chunk {chunk_id: $chunk_id})
                MERGE (w)-[r:RETRIEVED_CHUNK]->(c)
                SET r += $props
                """,
                workspace_id=workspace_id,
                chunk_id=chunk["chunk_id"],
                props=props,
            )

    driver.close()


def attach_multimodal_chunks_to_workspace(workspace_id: str, chunks: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        for chunk in chunks:
            props = {
                "score": chunk["score"],
                "modality": chunk.get("modality", "hybrid"),
                "document_type": chunk.get("document_type", "UNKNOWN"),
            }

            if chunk.get("architecture_state") is not None:
                props["architecture_state"] = chunk["architecture_state"]

            session.run(
                """
                MERGE (w:Workspace {workspace_id: $workspace_id})
                MATCH (c:MultiModalChunk {chunk_id: $chunk_id})
                MERGE (w)-[r:RETRIEVED_MULTIMODAL_CHUNK]->(c)
                SET r += $props
                """,
                workspace_id=workspace_id,
                chunk_id=chunk["chunk_id"],
                props=props,
            )

    driver.close()