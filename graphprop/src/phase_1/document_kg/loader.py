from src.phase_1.graph.connection import get_session


def save_chunk_to_neo4j(doc_name, chunk_id, text, embedding, source_path):
    """
    Guarda documento y chunks en Neo4j
    """

    query = """
    MERGE (d:Documento {nombre: $doc_name, ruta: $path})
    MERGE (c:Chunk {id: $chunk_id})
    SET c.texto = $text,
        c.embedding = $embedding
    MERGE (d)-[:TIENE]->(c)
    """

    try:
        with get_session() as session:
            session.run(
                query,
                doc_name=doc_name,
                chunk_id=chunk_id,
                text=text,
                embedding=embedding,
                path=source_path
            )

    except Exception as e:
        print(f"❌ Error guardando en Neo4j: {e}")