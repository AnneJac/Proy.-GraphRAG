from src.phase_1.graph.connection import get_driver
from src.phase_2.orchestration.gemini_multimodal import call_gemini_with_pdfs
from src.phase_2.retrieval.retrieval import get_bank_context


def build_bank_context_text(bank_context: dict) -> str:
    if not bank_context:
        return ""

    return f"""
CONTEXTO DEL BANCO:
- Nombre: {bank_context.get('name')}
- País: {bank_context.get('country')}
- Tier: {bank_context.get('tier')}
- Core bancario: {bank_context.get('core_banking_system')}
- Arquitectura empresarial / estilo arquitectónico: {bank_context.get('architecture_style')}
- Plataforma de datos: {bank_context.get('data_platform')}
""".strip()


def generate_workspace_proposal(workspace_id: str) -> str:
    driver = get_driver()

    with driver.session() as session:
        # -----------------------------
        # 1. Contexto textual recuperado
        # -----------------------------
        text_result = session.run(
            """
            MATCH (w:Workspace {workspace_id: $workspace_id})-[r:RETRIEVED_CHUNK]->(c:Chunk)<-[:HAS_CHUNK]-(d:SourceDocument)
            OPTIONAL MATCH (d)-[:BELONGS_TO]->(b:BankEntity)
            RETURN w.requirement_text AS requirement,
                   c.text AS chunk_text,
                   r.score AS score,
                   r.document_type AS document_type,
                   r.architecture_state AS architecture_state,
                   d.name AS document_name,
                   d.source_path AS source_path,
                   b.name AS bank_name
            ORDER BY r.score DESC
            LIMIT 8
            """,
            workspace_id=workspace_id,
        )
        text_rows = list(text_result)

        # ---------------------------------
        # 2. Contexto multimodal recuperado
        # ---------------------------------
        multimodal_result = session.run(
            """
            MATCH (w:Workspace {workspace_id: $workspace_id})-[r:RETRIEVED_MULTIMODAL_CHUNK]->(mm:MultiModalChunk)<-[:HAS_MULTIMODAL_CHUNK]-(d:SourceDocument)
            OPTIONAL MATCH (d)-[:BELONGS_TO]->(b:BankEntity)
            RETURN w.requirement_text AS requirement,
                   mm.retrieval_text AS retrieval_text,
                   mm.visual_summary AS visual_summary,
                   mm.modality AS modality,
                   mm.page_number AS page_number,
                   r.score AS score,
                   r.document_type AS document_type,
                   r.architecture_state AS architecture_state,
                   d.name AS document_name,
                   d.source_path AS source_path,
                   b.name AS bank_name
            ORDER BY r.score DESC
            LIMIT 5
            """,
            workspace_id=workspace_id,
        )
        multimodal_rows = list(multimodal_result)

    driver.close()

    if not text_rows and not multimodal_rows:
        return "No hay contexto suficiente."

    # ---------------------------------
    # 3. Requirement y banco del workspace
    # ---------------------------------
    requirement = None
    bank_name = None

    if text_rows:
        requirement = text_rows[0]["requirement"]
        bank_name = text_rows[0].get("bank_name")

    if not requirement and multimodal_rows:
        requirement = multimodal_rows[0]["requirement"]

    if not bank_name and multimodal_rows:
        bank_name = multimodal_rows[0].get("bank_name")

    bank_context = get_bank_context(bank_name) if bank_name else {}
    bank_context_text = build_bank_context_text(bank_context)

    # ---------------------------------
    # 4. Construcción de contexto textual
    # ---------------------------------
    text_context_blocks = []
    pdf_paths = []

    for i, row in enumerate(text_rows, 1):
        text_context_blocks.append(
            f"[Fuente textual {i} | Documento: {row['document_name']} | "
            f"Tipo: {row['document_type']} | "
            f"Estado: {row['architecture_state']} | "
            f"Score: {row['score']:.4f}]\n"
            f"{row['chunk_text']}"
        )

        source_path = row.get("source_path")
        if source_path and source_path not in pdf_paths:
            pdf_paths.append(source_path)

    # ---------------------------------
    # 5. Construcción de contexto multimodal
    # ---------------------------------
    multimodal_context_blocks = []

    for i, row in enumerate(multimodal_rows, 1):
        multimodal_context_blocks.append(
            f"[Fuente multimodal {i} | Documento: {row['document_name']} | "
            f"Página: {row['page_number']} | "
            f"Modalidad: {row['modality']} | "
            f"Tipo: {row['document_type']} | "
            f"Estado: {row['architecture_state']} | "
            f"Score: {row['score']:.4f}]\n"
            f"Resumen visual: {row['visual_summary']}\n"
            f"Texto de recuperación: {row['retrieval_text']}"
        )

        source_path = row.get("source_path")
        if source_path and source_path not in pdf_paths:
            pdf_paths.append(source_path)

    text_context = "\n\n".join(text_context_blocks) if text_context_blocks else "No se recuperó contexto textual."
    multimodal_context = (
        "\n\n".join(multimodal_context_blocks)
        if multimodal_context_blocks
        else "No se recuperó contexto multimodal."
    )

    # ---------------------------------
    # 6. Prompt final enriquecido
    # ---------------------------------
    prompt = f"""
Eres un comité experto en:
- Arquitectura empresarial
- Arquitectura de soluciones
- Infraestructura
- Ciberseguridad
- Desarrollo
- QA
- Riesgos tecnológicos

Debes generar una PROPUESTA TÉCNICA FINAL usando:
1. el requerimiento del cliente,
2. el contexto textual recuperado,
3. el contexto multimodal recuperado,
4. el contenido visual y estructural de los PDFs adjuntos,
5. y el contexto institucional del banco cuando esté disponible.

IMPORTANTE:
- Analiza no solo el texto, sino también diagramas, tablas, esquemas, gráficos e imágenes presentes en los PDFs.
- Usa el contexto del banco para contextualizar la propuesta cuando exista evidencia.
- No inventes información.
- Si una sección no tiene suficiente evidencia, indícalo explícitamente.
- Redacta en español formal, claro y profesional.
- Evita redundancias.
- Integra todo como una sola propuesta coherente, no como respuestas separadas por experto.
- Si hay elementos AS-IS y TO-BE, diferéncialos claramente.
- Prioriza consistencia, trazabilidad y aplicabilidad técnica.

REQUERIMIENTO:
{requirement}

{bank_context_text}

CONTEXTO TEXTUAL RECUPERADO:
{text_context}

CONTEXTO MULTIMODAL RECUPERADO:
{multimodal_context}

Genera la respuesta con esta estructura exacta:

1. Resumen ejecutivo
2. Entendimiento del requerimiento
3. Contexto institucional del banco
4. Hallazgos relevantes del contexto documental
5. Hallazgos visuales relevantes (diagramas, tablas, imágenes)
6. Arquitectura propuesta
7. Recomendaciones técnicas
8. Riesgos y dependencias
9. Conclusión
""".strip()

    # Para controlar costo y tiempo, empezamos con máximo 3 PDFs relevantes
    try:
        return call_gemini_with_pdfs(prompt, pdf_paths[:3])
    except Exception as e:
        return f"ERROR_GENERANDO_PROPUESTA: {str(e)}"