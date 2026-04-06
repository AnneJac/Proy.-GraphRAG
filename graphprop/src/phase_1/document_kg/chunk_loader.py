from src.phase_1.graph.connection import get_driver


def save_document_chunks(
    doc_name: str,
    source_path: str,
    file_hash: str,
    bank_name: str | None,
    project_name: str | None,
    document_type: str,
    architecture_state: str | None,
    chunks: list[dict]
):
    driver = get_driver()

    with driver.session() as session:
        session.run("""
            MERGE (d:SourceDocument {name: $doc_name})
            SET d.path = $source_path,
                d.file_hash = $file_hash,
                d.document_type = $document_type,
                d.architecture_state = $architecture_state,
                d.bank_name = $bank_name,
                d.project_name = $project_name
        """,
        doc_name=doc_name,
        source_path=source_path,
        file_hash=file_hash,
        document_type=document_type,
        architecture_state=architecture_state,
        bank_name=bank_name,
        project_name=project_name)

        if bank_name:
            session.run("""
                MATCH (d:SourceDocument {name: $doc_name})
                MATCH (b:BankEntity {name: $bank_name})
                MERGE (d)-[:DESCRIBES_BANK]->(b)
            """, doc_name=doc_name, bank_name=bank_name)

        if project_name:
            session.run("""
                MATCH (d:SourceDocument {name: $doc_name})
                MATCH (p:ProjectEntity {name: $project_name})
                MERGE (d)-[:DESCRIBES_PROJECT]->(p)
            """, doc_name=doc_name, project_name=project_name)

        session.run("""
            MERGE (dt:DocumentType {name: $document_type})
            WITH dt
            MATCH (d:SourceDocument {name: $doc_name})
            MERGE (d)-[:HAS_TYPE]->(dt)
        """, document_type=document_type, doc_name=doc_name)

        if architecture_state:
            session.run("""
                MERGE (a:ArchitectureState {name: $architecture_state})
                WITH a
                MATCH (d:SourceDocument {name: $doc_name})
                MERGE (d)-[:HAS_ARCHITECTURE_STATE]->(a)
            """, architecture_state=architecture_state, doc_name=doc_name)

        for chunk in chunks:
            session.run("""
                MERGE (c:Chunk {chunk_hash: $chunk_hash})
                SET c.chunk_id = coalesce(c.chunk_id, $chunk_id),
                    c.chunk_hash = coalesce(c.chunk_hash, $chunk_hash),
                    c.text = coalesce(c.text, $text),
                    c.embedding = coalesce(c.embedding, $embedding)

                WITH c
                MATCH (d:SourceDocument {name: $doc_name})
                MERGE (d)-[:HAS_CHUNK]->(c)
            """,
            chunk_hash=chunk["chunk_hash"],
            chunk_id=chunk["chunk_id"],
            text=chunk["text"],
            embedding=chunk["embedding"],
            doc_name=doc_name)

    driver.close()