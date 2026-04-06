import hashlib
from pathlib import Path

from src.phase_0.ingestion.pdf_reader import extract_text_from_pdf
from src.phase_0.ingestion.cleaner import clean_text
from src.phase_0.ingestion.chunking import chunk_text
from src.phase_0.ingestion.document_classifier import classify_document
from src.phase_2.embeddings.embedder import get_embedding

from src.phase_1.graph.connection import get_driver
from src.phase_1.document_kg.chunk_loader import save_document_chunks
from src.phase_1.document_kg.multimodal_chunker import build_multimodal_chunks
from src.phase_1.document_kg.multimodal_loader import save_multimodal_chunks


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def document_exists(driver, file_hash_val: str) -> bool:
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:SourceDocument {file_hash: $file_hash})
            RETURN count(d) AS total
            """,
            file_hash=file_hash_val,
        )
        return result.single()["total"] > 0


def get_existing_embedding(driver, chunk_hash_val: str):
    with driver.session() as session:
        result = session.run(
            """
            MATCH (c:Chunk {chunk_hash: $chunk_hash})
            RETURN c.embedding AS embedding
            """,
            chunk_hash=chunk_hash_val,
        )
        row = result.single()
        return row["embedding"] if row and row["embedding"] else None


def infer_bank_and_project_from_path(pdf_path: str) -> dict:
    path = Path(pdf_path)
    parts = path.parts

    bank_name = None
    project_name = None

    if "output" in parts:
        idx = parts.index("output")
        if len(parts) > idx + 1:
            bank_name = parts[idx + 1]
        if len(parts) > idx + 2:
            project_name = parts[idx + 2]

    return {
        "bank_name": bank_name,
        "project_name": project_name,
    }


def build_general_kg(source_dir: str):
    source_path = Path(source_dir).resolve()
    pdf_files = list(source_path.rglob("*.pdf"))

    if not pdf_files:
        print("No se encontraron PDFs.")
        return

    print(f"PDFs encontrados: {len(pdf_files)}")
    driver = get_driver()

    for pdf in pdf_files:
        print(f"\nProcesando: {pdf}")

        f_hash = file_hash(pdf)

        if document_exists(driver, f_hash):
            print("⏭️ Documento ya procesado, se omite")
            continue

        raw_text = extract_text_from_pdf(pdf)
        text = clean_text(raw_text)

        if not text:
            print("⚠️ PDF sin texto extraíble")
            continue

        doc_meta = classify_document(str(pdf))
        path_meta = infer_bank_and_project_from_path(str(pdf))

        # -------------------------
        # Chunks textuales
        # -------------------------
        raw_chunks = chunk_text(text, chunk_size=1200, overlap=150)

        chunk_payload = []
        reused = 0
        created = 0

        for i, chunk in enumerate(raw_chunks):
            c_hash = text_hash(chunk)

            embedding = get_existing_embedding(driver, c_hash)
            if embedding is not None:
                reused += 1
            else:
                embedding = get_embedding(chunk)
                if embedding is None:
                    continue
                created += 1

            chunk_payload.append(
                {
                    "chunk_id": f"{pdf.name}_{i}",
                    "chunk_hash": c_hash,
                    "text": chunk,
                    "embedding": embedding,
                }
            )

        save_document_chunks(
            doc_name=pdf.name,
            source_path=str(pdf),
            file_hash=f_hash,
            bank_name=path_meta["bank_name"],
            project_name=path_meta["project_name"],
            document_type=doc_meta["document_type"],
            architecture_state=doc_meta["architecture_state"],
            chunks=chunk_payload,
        )

        # -------------------------
        # Chunks multimodales
        # -------------------------
        try:
            multimodal_chunks = build_multimodal_chunks(
                pdf_path=str(pdf),
                document_type=doc_meta["document_type"],
                architecture_state=doc_meta["architecture_state"],
            )
        except Exception as exc:
            print(f"⚠️ Error generando multimodal chunks para {pdf.name}: {exc}")
            multimodal_chunks = []

        if multimodal_chunks:
            save_multimodal_chunks(
                doc_name=pdf.name,
                source_path=str(pdf),
                file_hash=f_hash,
                multimodal_chunks=multimodal_chunks,
            )

        print(f"✅ Documento guardado: {pdf.name}")
        print(f"✅ Tipo documental: {doc_meta['document_type']}")
        print(f"✅ Estado arquitectura: {doc_meta['architecture_state']}")
        print(f"✅ Chunks textuales guardados: {len(chunk_payload)}")
        print(f"✅ Chunks multimodales guardados: {len(multimodal_chunks)}")
        print(f"♻️ Embeddings reutilizados: {reused}")
        print(f"✨ Embeddings nuevos: {created}")

    driver.close()
    print("\n✅ KG documental actualizado")


if __name__ == "__main__":
    build_general_kg("output")