import json
import os
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from google import genai


DEFAULT_MODEL = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY.")
    return genai.Client(api_key=api_key)


def _safe_json_load(text: str) -> dict[str, Any]:
    """
    Intenta parsear JSON incluso si el modelo lo devuelve dentro de ```json ... ```
    """
    if not text:
        return {}

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "page_summary": cleaned,
            "visual_elements": [],
            "technical_components": [],
            "business_terms": [],
            "table_detected": False,
            "diagram_detected": False,
            "architecture_state": "UNKNOWN",
            "key_entities": [],
            "retrieval_text": cleaned,
            "confidence": "low",
        }


def _normalize_ascii_filename(name: str) -> str:
    """
    Convierte un nombre a una versión ASCII segura:
    - quita tildes
    - reemplaza espacios por guiones bajos
    - conserva extensión
    """
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace(" ", "_")

    safe_chars = []
    for ch in normalized:
        if ch.isalnum() or ch in {"_", "-", "."}:
            safe_chars.append(ch)
        else:
            safe_chars.append("_")

    safe_name = "".join(safe_chars).strip("._")
    return safe_name or "file"


def _path_needs_ascii_safe_copy(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def _prepare_ascii_safe_file(path: Path) -> tuple[Path, bool]:
    """
    Si la ruta original contiene caracteres no ASCII, crea una copia temporal
    con nombre/ruta segura para evitar errores al subir archivos a Gemini.

    Returns:
        (safe_path, should_cleanup)
    """
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    if not _path_needs_ascii_safe_copy(path):
        return path, False

    suffix = path.suffix or ""
    safe_name = _normalize_ascii_filename(path.stem) + suffix

    temp_dir = Path(tempfile.mkdtemp(prefix="gemini_upload_"))
    safe_path = temp_dir / safe_name

    shutil.copy2(path, safe_path)
    return safe_path, True


def _cleanup_temp_file(path: Path, should_cleanup: bool) -> None:
    """
    Elimina la carpeta temporal creada para archivos con ruta ASCII segura.
    """
    if not should_cleanup:
        return

    try:
        temp_dir = path.parent
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        # No frenamos el flujo por un problema al limpiar temporales
        pass


def build_multimodal_page_prompt(
    raw_text: str,
    document_type: str | None = None,
    architecture_state: str | None = None,
    page_number: int | None = None,
) -> str:
    page_label = f"Página: {page_number}" if page_number is not None else "Página: desconocida"
    doc_type = document_type or "UNKNOWN"
    arch_state = architecture_state or "UNKNOWN"

    return f"""
Analiza esta página de un documento técnico empresarial considerando tanto:
1. el contenido visual de la imagen de la página
2. el texto extraído de la página

Contexto:
- {page_label}
- document_type: {doc_type}
- architecture_state: {arch_state}

Texto extraído:
\"\"\"
{raw_text[:12000]}
\"\"\"

Tu objetivo es generar un chunk multimodal útil para recuperación en un sistema GraphRAG.

Devuelve SOLO un JSON válido con esta estructura:

{{
  "page_summary": "resumen breve y técnico de la página",
  "visual_elements": ["elemento visual 1", "elemento visual 2"],
  "technical_components": ["componente 1", "componente 2"],
  "business_terms": ["término 1", "término 2"],
  "table_detected": true,
  "diagram_detected": false,
  "architecture_state": "AS-IS | TO-BE | UNKNOWN",
  "key_entities": ["entidad 1", "entidad 2"],
  "retrieval_text": "texto enriquecido para embeddings y búsqueda semántica",
  "confidence": "high | medium | low"
}}

Reglas:
- Si hay diagrama, explica sus componentes y relaciones.
- Si hay tabla, resume su contenido de forma técnica.
- Si la imagen es decorativa, dilo de forma explícita.
- retrieval_text debe ser más rico que page_summary y útil para recuperación semántica.
- No agregues texto fuera del JSON.
""".strip()


def analyze_page_image(
    image_path: str,
    raw_text: str,
    document_type: str | None = None,
    architecture_state: str | None = None,
    page_number: int | None = None,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """
    Analiza una página renderizada (imagen) + texto extraído y devuelve JSON estructurado.
    Maneja rutas con caracteres no ASCII creando una copia temporal segura si hace falta.
    """
    original_path = Path(image_path)
    if not original_path.exists():
        raise FileNotFoundError(f"No existe la imagen de página: {image_path}")

    client = _get_client()

    safe_path, should_cleanup = _prepare_ascii_safe_file(original_path)

    try:
        uploaded_image = client.files.upload(file=str(safe_path))

        prompt = build_multimodal_page_prompt(
            raw_text=raw_text,
            document_type=document_type,
            architecture_state=architecture_state,
            page_number=page_number,
        )

        response = client.models.generate_content(
            model=model,
            contents=[prompt, uploaded_image],
        )

        text = response.text if getattr(response, "text", None) else ""
        data = _safe_json_load(text)

        data.setdefault("page_summary", "")
        data.setdefault("visual_elements", [])
        data.setdefault("technical_components", [])
        data.setdefault("business_terms", [])
        data.setdefault("table_detected", False)
        data.setdefault("diagram_detected", False)
        data.setdefault("architecture_state", architecture_state or "UNKNOWN")
        data.setdefault("key_entities", [])
        data.setdefault("retrieval_text", data.get("page_summary", ""))
        data.setdefault("confidence", "low")

        return data

    finally:
        _cleanup_temp_file(safe_path, should_cleanup)


def call_gemini_with_pdfs(prompt: str, pdf_paths: list[str], model: str = DEFAULT_MODEL) -> str:
    """
    Se mantiene por compatibilidad con tu flujo actual de análisis multimodal final.
    Maneja rutas con caracteres no ASCII creando copias temporales seguras cuando haga falta.
    """
    client = _get_client()

    uploaded_files = []
    temp_files_to_cleanup: list[tuple[Path, bool]] = []

    try:
        for pdf_path in pdf_paths:
            original_path = Path(pdf_path)

            if not original_path.exists() or original_path.suffix.lower() != ".pdf":
                continue

            safe_path, should_cleanup = _prepare_ascii_safe_file(original_path)
            temp_files_to_cleanup.append((safe_path, should_cleanup))

            uploaded = client.files.upload(file=str(safe_path))
            uploaded_files.append(uploaded)

        if not uploaded_files:
            return "ERROR: No se encontraron PDFs válidos para análisis multimodal."

        response = client.models.generate_content(
            model=model,
            contents=[prompt, *uploaded_files],
        )

        return response.text if getattr(response, "text", None) else "No se obtuvo respuesta del modelo."

    except UnicodeEncodeError as exc:
        return (
            "ERROR: Falló la subida de archivos por caracteres no ASCII en la ruta o nombre "
            f"del archivo. Detalle: {exc}"
        )
    except Exception as exc:
        return f"ERROR: Falló la llamada multimodal a Gemini. Detalle: {exc}"
    finally:
        for safe_path, should_cleanup in temp_files_to_cleanup:
            _cleanup_temp_file(safe_path, should_cleanup)