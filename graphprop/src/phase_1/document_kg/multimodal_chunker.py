import hashlib
import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from src.phase_0.ingestion.cleaner import clean_text
from src.phase_2.embeddings.embedder import get_embedding
from src.phase_2.orchestration.gemini_multimodal import analyze_page_image


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _render_page_to_image(page: fitz.Page, image_path: Path, zoom: float = 2.0) -> None:
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(image_path))


def _extract_text_by_page(pdf_path: str) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    pages: list[dict[str, Any]] = []

    for i, page in enumerate(doc):
        raw_text = page.get_text("text") or ""
        pages.append(
            {
                "page_number": i + 1,
                "raw_text": clean_text(raw_text),
                "page": page,
            }
        )

    return pages


def _should_create_multimodal_chunk(
    raw_text: str,
    document_type: str | None = None,
) -> bool:
    """
    Regla simple y segura para tesis:
    - si la página tiene algo de texto, se procesa
    - si el documento es TECHNICAL_ANNEX, también se procesa aunque tenga poco texto
    """
    if raw_text and len(raw_text.strip()) >= 30:
        return True

    if (document_type or "").upper() in {"TECHNICAL_ANNEX", "ARCHITECTURE", "RFP", "RFP_QA"}:
        return True

    return False


def _infer_modality(gemini_result: dict[str, Any], raw_text: str) -> str:
    if gemini_result.get("table_detected"):
        return "table"
    if gemini_result.get("diagram_detected"):
        return "image"
    if raw_text:
        return "hybrid"
    return "image"


def _build_retrieval_text(
    gemini_result: dict[str, Any],
    raw_text: str,
    page_number: int,
    document_type: str | None,
    architecture_state: str | None,
) -> str:
    page_summary = gemini_result.get("page_summary", "")
    technical_components = ", ".join(gemini_result.get("technical_components", []))
    business_terms = ", ".join(gemini_result.get("business_terms", []))
    key_entities = ", ".join(gemini_result.get("key_entities", []))
    visual_elements = ", ".join(gemini_result.get("visual_elements", []))

    pieces = [
        f"Página {page_number} del documento tipo {document_type or 'UNKNOWN'} con estado de arquitectura {architecture_state or 'UNKNOWN'}.",
        page_summary,
    ]

    if technical_components:
        pieces.append(f"Componentes técnicos: {technical_components}.")
    if business_terms:
        pieces.append(f"Términos de negocio: {business_terms}.")
    if key_entities:
        pieces.append(f"Entidades clave: {key_entities}.")
    if visual_elements:
        pieces.append(f"Elementos visuales: {visual_elements}.")
    if raw_text:
        pieces.append(f"Texto extraído relevante: {raw_text[:1500]}")

    return " ".join(piece for piece in pieces if piece).strip()


def build_multimodal_chunks(
    pdf_path: str,
    document_type: str | None = None,
    architecture_state: str | None = None,
    rendered_base_dir: str = "output/rendered_pages",
) -> list[dict[str, Any]]:
    """
    Genera un chunk multimodal por página.
    Cada chunk incluye:
    - imagen renderizada de la página
    - texto extraído
    - análisis Gemini
    - embedding del retrieval_text
    """
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    rendered_root = Path(rendered_base_dir) / pdf.stem
    page_entries = _extract_text_by_page(str(pdf))
    multimodal_chunks: list[dict[str, Any]] = []

    doc = fitz.open(str(pdf))
    try:
        for idx, page_info in enumerate(page_entries):
            page_number = page_info["page_number"]
            raw_text = page_info["raw_text"]

            if not _should_create_multimodal_chunk(raw_text, document_type):
                continue

            page = doc[idx]
            image_path = rendered_root / f"page_{page_number}.png"
            _render_page_to_image(page, image_path)

            try:
                gemini_result = analyze_page_image(
                    image_path=str(image_path),
                    raw_text=raw_text,
                    document_type=document_type,
                    architecture_state=architecture_state,
                    page_number=page_number,
                )
            except Exception as exc:
                gemini_result = {
                    "page_summary": f"Fallback local: no se pudo analizar multimodalmente la página {page_number}. Error: {exc}",
                    "visual_elements": [],
                    "technical_components": [],
                    "business_terms": [],
                    "table_detected": False,
                    "diagram_detected": False,
                    "architecture_state": architecture_state or "UNKNOWN",
                    "key_entities": [],
                    "retrieval_text": raw_text[:2000],
                    "confidence": "low",
                }

            retrieval_text = gemini_result.get("retrieval_text") or _build_retrieval_text(
                gemini_result=gemini_result,
                raw_text=raw_text,
                page_number=page_number,
                document_type=document_type,
                architecture_state=architecture_state,
            )

            embedding = get_embedding(retrieval_text)
            if embedding is None:
                continue

            chunk_id = f"{pdf.stem}_mm_{page_number}"
            chunk_hash = _sha256_text(retrieval_text)

            multimodal_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_hash": chunk_hash,
                    "page_id": f"{pdf.stem}_page_{page_number}",
                    "page_number": page_number,
                    "source_path": str(pdf.resolve()),
                    "image_path": str(image_path.resolve()),
                    "modality": _infer_modality(gemini_result, raw_text),
                    "chunk_type": "page_summary",
                    "raw_text": raw_text,
                    "visual_summary": gemini_result.get("page_summary", ""),
                    "table_content": "",
                    "llm_summary": gemini_result.get("page_summary", ""),
                    "retrieval_text": retrieval_text,
                    "embedding": embedding,
                    "document_type": document_type or "UNKNOWN",
                    "architecture_state": gemini_result.get("architecture_state", architecture_state or "UNKNOWN"),
                    "table_detected": gemini_result.get("table_detected", False),
                    "diagram_detected": gemini_result.get("diagram_detected", False),
                    "technical_components_json": json.dumps(gemini_result.get("technical_components", []), ensure_ascii=False),
                    "business_terms_json": json.dumps(gemini_result.get("business_terms", []), ensure_ascii=False),
                    "key_entities_json": json.dumps(gemini_result.get("key_entities", []), ensure_ascii=False),
                    "visual_elements_json": json.dumps(gemini_result.get("visual_elements", []), ensure_ascii=False),
                    "confidence": gemini_result.get("confidence", "low"),
                }
            )
    finally:
        doc.close()

    return multimodal_chunks