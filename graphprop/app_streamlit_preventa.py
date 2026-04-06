from __future__ import annotations

from io import BytesIO
from datetime import datetime
import os
import re
import json
import time
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import streamlit as st
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

import re

def clean_markdown(text: str) -> str:
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'^\*\s+', '', text)
    text = re.sub(r'^\-\s+', '', text)
    return text.strip()

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None
from src.phase_2.retrieval.retrieval import retrieve_hybrid_context, get_bank_context
from src.phase_2.workspace.workspace_loader import (
    attach_chunks_to_workspace,
    attach_multimodal_chunks_to_workspace,
    create_workspace,
)
from src.phase_2.orchestration.proposal_generator import generate_workspace_proposal


# ==========================================================
# CONFIGURACIÓN PRINCIPAL
# ==========================================================
PROJECT_ROOT = Path(r"C:\Projects\Udla\AI\TITULACION\Proyecto_GraphRAG_2\graphprop")
BASE_OUTPUT = PROJECT_ROOT / "output"
REPORTS_DIR = BASE_OUTPUT / "reports"

BUILD_GENERAL_KG_CMD = ["python", "-m", "scripts.phase_1.build_general_kg"]
BUILD_MASTER_KG_CMD = ["python", "-m", "scripts.phase_1.build_master_kg"]
GENERATE_PROPOSAL_CMD = ["python", "-m", "scripts.phase_2.generate_proposal"]

ALLOWED_EXTENSIONS = {".pdf"}
FINAL_FOLDER_NAME = "RFP"
MAX_FILE_MB = 200

DOC_TYPE_PATTERNS = {
    "RFP_QA": [r"\brfp[_\s-]?qa\b", r"\bqa\b"],
    "MEETING": [r"\bmeeting\b", r"minutes", r"acta", r"reunion", r"reunión"],
    "TECHNICAL_ANNEX_AS_IS": [r"technical[_\s-]?annex", r"as[_\s-]?is", r"arquitectura[_\s-]?as[_\s-]?is"],
    "TECHNICAL_ANNEX_TO_BE": [r"technical[_\s-]?annex", r"to[_\s-]?be", r"arquitectura[_\s-]?to[_\s-]?be"],
    "RFP": [r"\brfp\b"],
}

DOC_TYPE_HELP = {
    "RFP": "Documento base de requerimientos del proyecto.",
    "RFP_QA": "Preguntas y respuestas o aclaraciones del RFP.",
    "MEETING": "Minutas, reuniones, sesiones de levantamiento o workshops.",
    "TECHNICAL_ANNEX_AS_IS": "Anexo técnico de arquitectura actual AS-IS.",
    "TECHNICAL_ANNEX_TO_BE": "Anexo técnico de arquitectura objetivo TO-BE.",
    "UNKNOWN": "No se pudo clasificar automáticamente por nombre; conviene revisar el nombre del archivo.",
}


# ==========================================================
# ESTILOS / DISEÑO
# ==========================================================
def inject_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: #f2f2f2;
        }}

        [data-testid="stSidebar"] {{
            background: #156688;
            border-right: 2px solid #0d3b53;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            min-height: 64px;
            border-radius: 16px;
            border: 2px solid #0a2f43;
            background: #0a3e57;
            color: white;
            font-size: 18px;
            font-weight: 800;
            box-shadow: 8px 8px 14px rgba(255,255,255,0.15);
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            border-color: #0a2f43;
            color: white;
        }}

        .page-wrap {{
            padding: 8px 8px 24px 8px;
        }}

        .hero-box {{
            background: #156688;
            border: 2px solid #0a3549;
            padding: 34px 28px 48px 28px;
            margin: 10px auto 18px auto;
            max-width: 980px;
        }}

        .hero-title {{
            color: white;
            font-size: 48px;
            line-height: 1.15;
            font-weight: 900;
            text-align: center;
            margin-bottom: 28px;
        }}

        .hero-subtitle {{
            color: white;
            font-size: 18px;
            text-align: center;
            font-weight: 650;
            max-width: 860px;
            margin: 0 auto;
        }}

        .main-title {{
            color: #1b2740;
            font-size: 34px;
            font-weight: 900;
            text-align: center;
            margin-top: 2px;
            margin-bottom: 4px;
        }}

        .top-line {{
            height: 2px;
            background: #156688;
            margin-bottom: 8px;
        }}

        .section-card {{
            background: #f5f6f8;
            border-radius: 8px;
            padding: 8px;
        }}

        .folder-title {{
            font-size: 18px;
            font-weight: 900;
            color: #202020;
            margin-bottom: 10px;
        }}

        .big-action button {{
            min-height: 90px !important;
            border-radius: 22px !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            background: #b9d8e7 !important;
            color: white !important;
            border: 2px solid #0a2f43 !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.35) !important;
        }}

        .start-btn button {{
            min-height: 64px !important;
            border-radius: 14px !important;
            font-size: 20px !important;
            font-weight: 900 !important;
            background: #0a3e57 !important;
            color: white !important;
            border: 1px solid #0a2f43 !important;
            box-shadow: 0 6px 12px rgba(0,0,0,0.20) !important;
        }}

        .tiny-muted {{
            color: #6e7783;
            font-size: 12px;
            margin-top: 8px;
        }}

        .status-pill {{
            display: inline-block;
            background: #e7eef2;
            color: #183041;
            font-size: 12px;
            padding: 6px 10px;
            border-radius: 999px;
            margin-right: 8px;
            margin-bottom: 8px;
            font-weight: 800;
        }}

        .upload-tip {{
            background: #eef5f8;
            border-left: 4px solid #156688;
            padding: 10px 12px;
            border-radius: 8px;
            color: #183041;
            font-size: 13px;
            margin-top: 8px;
            margin-bottom: 10px;
        }}

        .detect-card {{
            background: white;
            border: 1px solid #d8e3ea;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }}

        .detect-title {{
            font-weight: 900;
            color: #1b2740;
            margin-bottom: 4px;
        }}

        .ok-chip, .warn-chip, .info-chip {{
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 900;
            margin-right: 6px;
            margin-top: 6px;
        }}

        .ok-chip {{
            background: #dff5e5;
            color: #116530;
        }}

        .warn-chip {{
            background: #ffe7cf;
            color: #915300;
        }}

        .info-chip {{
            background: #e5eef9;
            color: #18426d;
        }}

        [data-testid="stFileUploader"] {{
            width: 100% !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            min-height: 170px !important;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 16px !important;
            background: #252833;
            border: 1px solid #30384b;
            padding-top: 8px;
            padding-bottom: 8px;
        }}

        [data-testid="stFileUploaderDropzone"] > div {{
            text-align: center;
            width: 100%;
        }}

        [data-testid="stFileUploaderDropzone"] svg {{
            width: 52px !important;
            height: 52px !important;
        }}

        [data-testid="stFileUploaderDropzone"] p {{
            font-size: 0 !important;
        }}

        [data-testid="stFileUploaderDropzone"] p::after {{
            content: "Arrastra o selecciona";
            font-size: 24px;
            font-weight: 800;
            color: white;
            display: block;
            margin-top: 8px;
        }}

        [data-testid="stFileUploaderDropzone"] small {{
            font-size: 0 !important;
        }}

        [data-testid="stFileUploaderDropzone"] small::after {{
            content: "Límite {MAX_FILE_MB} MB por PDF · Tipos: RFP, RFP_QA, MEETING, TECHNICAL_ANNEX Arquitectura AS-IS y TO-BE";
            font-size: 12px;
            color: #cdd4df;
            display: block;
            margin-top: 8px;
            line-height: 1.45;
        }}

        .pulse-upload {{
            animation: pulseGlow 1.25s ease-in-out infinite;
        }}

        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 0 rgba(21,102,136,0.2); transform: scale(1); }}
            50% {{ box-shadow: 0 0 18px rgba(21,102,136,0.45); transform: scale(1.01); }}
            100% {{ box-shadow: 0 0 0 rgba(21,102,136,0.2); transform: scale(1); }}
        }}

        /* ===== FIX EXPANDER (Archivos guardados) ===== */

        [data-testid="stExpanderDetails"] {{
            background: #ffffff !important;
            padding: 12px 14px;
            border-radius: 0 0 10px 10px;
        }}

        [data-testid="stExpanderDetails"] * {{
            color: #1b2740 !important;
        }}

        [data-testid="stExpanderDetails"] ul,
        [data-testid="stExpanderDetails"] li,
        [data-testid="stExpanderDetails"] p {{
            color: #1b2740 !important;
            font-weight: 600;
        }}

        /* ===== PROPUESTA TEXTO ===== */

        .proposal-box {{
            background: #ffffff;
            color: #1b2740 !important;
            font-size: 15px;
            line-height: 1.75;
            font-weight: 500;
            padding: 22px 24px;
            border-radius: 14px;
            border: 1px solid #dfe6ee;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06);
            white-space: pre-wrap;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# HELPERS GENERALES
# ==========================================================
def init_state() -> None:
    defaults = {
        "page": "inicio",
        "last_saved_files": [],
        "last_build_results": [],
        "last_proposal_text": "",
        "last_proposal_log": "",
        "last_selected_bank": "",
        "last_selected_project": "",
        "last_validation_results": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value



def normalize_folder_name(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text



def safe_slug(text: str) -> str:
    text = normalize_folder_name(text)
    text = re.sub(r'[^\w\s\-áéíóúÁÉÍÓÚñÑ]', '', text)
    return text.strip()



def build_target_path(bank: str, project: str) -> Path:
    bank_clean = safe_slug(bank)
    project_clean = safe_slug(project)
    return BASE_OUTPUT / bank_clean / project_clean / FINAL_FOLDER_NAME



def ensure_project_structure(bank: str, project: str) -> Path:
    target_dir = build_target_path(bank, project)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir



def file_size_mb(file_bytes: bytes) -> float:
    return len(file_bytes) / (1024 * 1024)



def sha256_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()



def detect_document_type(filename: str) -> str:
    name = filename.lower()

    if any(re.search(p, name) for p in DOC_TYPE_PATTERNS["TECHNICAL_ANNEX_AS_IS"]):
        return "TECHNICAL_ANNEX_AS_IS"
    if any(re.search(p, name) for p in DOC_TYPE_PATTERNS["TECHNICAL_ANNEX_TO_BE"]):
        return "TECHNICAL_ANNEX_TO_BE"
    if any(re.search(p, name) for p in DOC_TYPE_PATTERNS["RFP_QA"]):
        return "RFP_QA"
    if any(re.search(p, name) for p in DOC_TYPE_PATTERNS["MEETING"]):
        return "MEETING"
    if any(re.search(p, name) for p in DOC_TYPE_PATTERNS["RFP"]):
        return "RFP"
    return "UNKNOWN"



def validate_uploaded_files(uploaded_files) -> List[Dict[str, object]]:
    validations: List[Dict[str, object]] = []

    for uploaded_file in uploaded_files or []:
        filename = uploaded_file.name
        suffix = Path(filename).suffix.lower()
        file_bytes = uploaded_file.getvalue()
        size_mb = file_size_mb(file_bytes)
        detected_type = detect_document_type(filename)
        valid_ext = suffix in ALLOWED_EXTENSIONS
        valid_size = size_mb <= MAX_FILE_MB
        is_valid = valid_ext and valid_size

        validations.append(
            {
                "name": filename,
                "ext": suffix,
                "size_mb": round(size_mb, 2),
                "detected_type": detected_type,
                "valid_ext": valid_ext,
                "valid_size": valid_size,
                "is_valid": is_valid,
                "sha256": sha256_bytes(file_bytes),
                "help": DOC_TYPE_HELP.get(detected_type, DOC_TYPE_HELP["UNKNOWN"]),
                "bytes": file_bytes,
            }
        )

    return validations



def save_validated_files(validations: List[Dict[str, object]], target_dir: Path) -> List[Path]:
    saved_paths: List[Path] = []
    valid_items = [v for v in validations if bool(v["is_valid"])]

    if not valid_items:
        return saved_paths

    progress = st.progress(0, text="Preparando carga...")
    status_box = st.empty()
    anim_box = st.empty()
    anim_box.markdown(
        '<div class="upload-tip pulse-upload">Subiendo archivos al sistema...</div>',
        unsafe_allow_html=True,
    )

    total = len(valid_items)
    for idx, item in enumerate(valid_items, start=1):
        filename = str(item["name"])
        status_box.info(f"Guardando {idx}/{total}: {filename}")
        file_path = target_dir / filename
        with open(file_path, "wb") as f:
            f.write(item["bytes"])
        saved_paths.append(file_path)
        progress.progress(idx / total, text=f"Progreso de carga: {idx}/{total} archivo(s)")
        time.sleep(0.12)

    status_box.success("Carga completada.")
    anim_box.empty()
    return saved_paths



def list_banks_from_output() -> List[str]:
    if not BASE_OUTPUT.exists():
        return []
    return sorted([p.name for p in BASE_OUTPUT.iterdir() if p.is_dir() and p.name != "reports"])



def list_projects_from_output(bank: str) -> List[str]:
    if not bank:
        return []
    bank_path = BASE_OUTPUT / bank
    if not bank_path.exists():
        return []
    return sorted([p.name for p in bank_path.iterdir() if p.is_dir()])



def list_files_for_project(bank: str, project: str) -> List[str]:
    project_path = build_target_path(bank, project)
    if not project_path.exists():
        return []
    return sorted([p.name for p in project_path.iterdir() if p.is_file()])



def read_env_file() -> Dict[str, str]:
    env_path = PROJECT_ROOT / ".env"
    env_vars: Dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars



def resolve_runtime_env() -> Dict[str, str]:
    env = os.environ.copy()
    env.update(read_env_file())
    pythonpath = env.get("PYTHONPATH", "")
    project_root_str = str(PROJECT_ROOT)
    if project_root_str not in pythonpath:
        env["PYTHONPATH"] = f"{project_root_str}{os.pathsep}{pythonpath}" if pythonpath else project_root_str
    return env



def run_command(command: List[str], workdir: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(workdir) if workdir else None,
            env=env,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        combined_output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        return result.returncode == 0, combined_output
    except Exception as exc:
        return False, str(exc)



def run_build_pipeline(run_general: bool = True, run_master: bool = True) -> List[Dict[str, str]]:
    runtime_env = resolve_runtime_env()
    results: List[Dict[str, str]] = []

    pipeline_bar = st.progress(0, text="Iniciando construcción del grafo...")
    current_step = 0
    total_steps = int(run_general) + int(run_master)

    if run_general:
        current_step += 1
        pipeline_bar.progress((current_step - 0.5) / total_steps, text="Ejecutando build_general_kg...")
        ok, log = run_command(BUILD_GENERAL_KG_CMD, PROJECT_ROOT, runtime_env)
        results.append({"name": "build_general_kg", "success": ok, "log": log})
        pipeline_bar.progress(current_step / total_steps, text="build_general_kg finalizado")

    if run_master:
        current_step += 1
        pipeline_bar.progress((current_step - 0.5) / total_steps, text="Ejecutando build_master_kg...")
        ok, log = run_command(BUILD_MASTER_KG_CMD, PROJECT_ROOT, runtime_env)
        results.append({"name": "build_master_kg", "success": ok, "log": log})
        pipeline_bar.progress(current_step / total_steps, text="build_master_kg finalizado")

    return results


# ==========================================================
# NEO4J
# ==========================================================
def get_neo4j_driver():
    if GraphDatabase is None:
        return None

    env = resolve_runtime_env()
    uri = env.get("NEO4J_URI") or env.get("AURA_URI") or env.get("GRAPH_URI") or ""
    user = env.get("NEO4J_USERNAME") or env.get("NEO4J_USER") or env.get("AURA_USERNAME") or ""
    password = env.get("NEO4J_PASSWORD") or env.get("AURA_PASSWORD") or env.get("GRAPH_PASSWORD") or ""

    if not uri or not user or not password:
        return None

    try:
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception:
        return None



def query_banks_from_graph() -> List[str]:
    driver = get_neo4j_driver()
    if driver is None:
        return []

    cypher_candidates = [
        "MATCH (b:BankEntity) RETURN DISTINCT coalesce(b.name, b.bank_name) AS name ORDER BY name",
        "MATCH (b:Bank) RETURN DISTINCT coalesce(b.name, b.bank_name) AS name ORDER BY name",
    ]

    try:
        with driver.session() as session:
            for query in cypher_candidates:
                try:
                    records = session.run(query)
                    banks = [r["name"] for r in records if r.get("name")]
                    if banks:
                        return banks
                except Exception:
                    continue
        return []
    finally:
        driver.close()



def query_projects_from_graph(bank: str) -> List[str]:
    driver = get_neo4j_driver()
    if driver is None or not bank:
        return []

    cypher_candidates = [
        "MATCH (p:ProjectEntity)-[:BELONGS_TO]->(b:BankEntity) WHERE coalesce(b.name, b.bank_name) = $bank RETURN DISTINCT coalesce(p.name, p.project_name) AS name ORDER BY name",
        "MATCH (b:BankEntity)<-[:FOR_BANK]-(p:ProjectEntity) WHERE coalesce(b.name, b.bank_name) = $bank RETURN DISTINCT coalesce(p.name, p.project_name) AS name ORDER BY name",
        "MATCH (p:Project)-[:BELONGS_TO]->(b:Bank) WHERE coalesce(b.name, b.bank_name) = $bank RETURN DISTINCT coalesce(p.name, p.project_name) AS name ORDER BY name",
    ]

    try:
        with driver.session() as session:
            for query in cypher_candidates:
                try:
                    records = session.run(query, bank=bank)
                    projects = [r["name"] for r in records if r.get("name")]
                    if projects:
                        return projects
                except Exception:
                    continue
        return []
    finally:
        driver.close()



def get_available_banks() -> List[str]:
    graph_banks = query_banks_from_graph()
    if graph_banks:
        return sorted(graph_banks)
    return list_banks_from_output()



def get_available_projects(bank: str) -> List[str]:
    graph_projects = query_projects_from_graph(bank)
    if graph_projects:
        return sorted(graph_projects)
    return list_projects_from_output(bank)


def workspace_exists(workspace_id: str) -> bool:
    driver = get_neo4j_driver()
    if driver is None:
        return False

    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (w:Workspace {workspace_id: $id}) RETURN w LIMIT 1",
                id=workspace_id
            )
            return result.single() is not None
    except Exception:
        return False
    finally:
        driver.close()

def build_workspace_direct(workspace_id: str, requirement_text: str, bank_name: str) -> Tuple[bool, str]:
    try:
        create_workspace(
            workspace_id=workspace_id,
            requirement_text=requirement_text,
            preferred_doc_types=[],
            preferred_arch_state=None,
        )

        retrieval_result = retrieve_hybrid_context(
            requirement_text=requirement_text,
            preferred_doc_types=[],
            preferred_arch_state=None,
            bank_name=bank_name,
            top_k_text=5,
            top_k_multimodal=3,
        )

        text_chunks = retrieval_result["text_chunks"]
        multimodal_chunks = retrieval_result["multimodal_chunks"]

        if text_chunks:
            attach_chunks_to_workspace(workspace_id, text_chunks)

        if multimodal_chunks:
            attach_multimodal_chunks_to_workspace(workspace_id, multimodal_chunks)

        log = (
            f"✅ Workspace creado/actualizado: {workspace_id}\n"
            f"✅ Banco filtrado: {bank_name}\n"
            f"✅ Chunks textuales vinculados: {len(text_chunks)}\n"
            f"✅ Chunks multimodales vinculados: {len(multimodal_chunks)}"
        )
        log += "\n\n--- Top text chunks ---"
        for chunk in text_chunks:
            log += f"\n{chunk['chunk_id']} | score={chunk['score']:.4f}"

        log += "\n\n--- Top multimodal chunks ---"
        for chunk in multimodal_chunks:
            log += f"\n{chunk['chunk_id']} | score={chunk['score']:.4f}"
        return True, log

    except Exception as e:
        return False, str(e)


def render_connection_status() -> None:
    neo_ok = get_neo4j_driver() is not None
    env_exists = (PROJECT_ROOT / ".env").exists()

    def status(label, ok):
        color = "#dff5e5" if ok else "#fde2e1"
        text_color = "#116530" if ok else "#a61b1b"
        icon = "🟢" if ok else "🔴"

        return f"""
        <div style="
            background:{color};
            color:{text_color};
            padding:8px 12px;
            border-radius:10px;
            font-size:13px;
            font-weight:700;
            margin-bottom:6px;
            width:100%;
        ">
            {icon} {label}
        </div>
        """

    st.markdown(
        f"""
        <div>
            {status("Proyecto", PROJECT_ROOT.exists())}
            {status("Output", BASE_OUTPUT.exists())}
            {status("Conexión API", env_exists)}
            {status("Grafo", neo_ok)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# PROPUESTAS
# ==========================================================
def try_direct_proposal_generation(bank: str, project: str, prompt: str) -> Tuple[bool, str]:
    try:
        from src.phase_2.orchestration.proposal_generator import ProposalGenerator  # type: ignore

        generator = ProposalGenerator()

        if hasattr(generator, "generate"):
            result = generator.generate(
                bank_name=bank or None,
                project_name=project or None,
                user_prompt=prompt or None,
            )
            if isinstance(result, str):
                return True, result
            if isinstance(result, dict):
                for key in ["proposal", "text", "final_text", "result"]:
                    if key in result and result[key]:
                        return True, str(result[key])
                return True, json.dumps(result, ensure_ascii=False, indent=2)
        return False, "La clase ProposalGenerator existe pero no expone un método generate compatible."
    except Exception as exc:
        return False, str(exc)



def try_cli_proposal_generation(bank: str, project: str, prompt: str) -> Tuple[bool, str, str]:
    env = resolve_runtime_env()
    attempts = []

    if bank and project and prompt:
        attempts.append(GENERATE_PROPOSAL_CMD + ["--bank", bank, "--project", project, "--prompt", prompt])
    if bank and project:
        attempts.append(GENERATE_PROPOSAL_CMD + ["--bank", bank, "--project", project])
    if prompt:
        attempts.append(GENERATE_PROPOSAL_CMD + ["--prompt", prompt])
    if bank:
        attempts.append(GENERATE_PROPOSAL_CMD + ["--bank", bank])
    attempts.append(GENERATE_PROPOSAL_CMD)

    for attempt in attempts:
        ok, log = run_command(attempt, PROJECT_ROOT, env)
        if ok:
            return True, "", log

    return False, "No se pudo confirmar la firma del CLI de generate_proposal. Revisa los logs y ajusta los argumentos si tu script usa otros nombres.", "\n\n".join([f"Intento: {' '.join(a)}" for a in attempts])



def generate_proposal(bank: str, project: str, prompt: str) -> Tuple[bool, str, str]:
    workspace_id = f"{safe_slug(bank)}_{safe_slug(project)}"

    if not prompt.strip():
        prompt = (
            f"Generar propuesta técnica para el banco {bank} y el proyecto {project}. "
            f"Considerar requerimientos funcionales, requerimientos técnicos, "
            f"arquitectura actual AS-IS, arquitectura objetivo TO-BE, "
            f"documentos RFP, RFP_QA, reuniones y anexos técnicos relacionados."
        )

    build_log = ""

    try:
        if not workspace_exists(workspace_id):
            ok_build, build_log = build_workspace_direct(
                workspace_id=workspace_id,
                requirement_text=prompt,
                bank_name=bank,
            )
            if not ok_build:
                return False, "Error construyendo workspace.", build_log
        else:
            build_log = f"Workspace ya existente, se reutiliza: {workspace_id}"

        proposal = generate_workspace_proposal(workspace_id)

        if not proposal:
            return False, "No se generó propuesta.", build_log

        if proposal.strip() == "No hay contexto suficiente.":
            return False, proposal, build_log

        return True, proposal, build_log

    except Exception as e:
        return False, "Error generando propuesta.", build_log + "\n\n" + str(e)

# ==========================================================
# UI HELPERS
# ==========================================================
def sidebar_navigation() -> None:
    with st.sidebar:
        st.markdown(" ")
        st.markdown("### Navegación")

        if st.button("Subir archivos", use_container_width=True):
            st.session_state.page = "subir"
            st.rerun()

        st.write("")
        if st.button("Generar propuesta", use_container_width=True):
            st.session_state.page = "propuesta"
            st.rerun()

        st.write("")
        st.write("")
        with st.expander("⚙️ Estado del sistema", expanded=False):
            render_connection_status()


def page_header(title: str) -> None:
    st.markdown(f'<div class="main-title">{title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="top-line"></div>', unsafe_allow_html=True)



def render_home() -> None:
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero-box">
            <div class="hero-title">App para Sistema de soporte a<br>la decisión para preventa<br>técnica</div>
            <div class="hero-subtitle">
                Plataforma para registrar documentación técnica de proyectos y sustento de consulta y generación de respuestas estructuradas para apoyar la elaboración de propuestas técnicas.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([4, 1, 1.2])
    with right:
        st.markdown('<div class="start-btn">', unsafe_allow_html=True)
        if st.button("Iniciar", use_container_width=True):
            st.session_state.page = "subir"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)



def render_validation_results(validations: List[Dict[str, object]]) -> None:
    if not validations:
        return

    st.subheader("Validación automática de documentos")
    for item in validations:
        detected_type = str(item["detected_type"])
        chip_class = "ok-chip" if item["is_valid"] and detected_type != "UNKNOWN" else "warn-chip" if detected_type == "UNKNOWN" else "warn-chip"
        size_status = "OK" if item["valid_size"] else "Excede límite"
        ext_status = "PDF válido" if item["valid_ext"] else "Extensión no permitida"
        validity = "Listo para guardar" if item["is_valid"] else "Requiere corrección"

        st.markdown(
            f"""
            <div class="detect-card">
                <div class="detect-title">{item['name']}</div>
                <div>{item['help']}</div>
                <div class="{chip_class}">Tipo detectado: {detected_type}</div>
                <div class="info-chip">Tamaño: {item['size_mb']} MB</div>
                <div class="info-chip">{ext_status}</div>
                <div class="{'ok-chip' if item['valid_size'] else 'warn-chip'}">{size_status}</div>
                <div class="{'ok-chip' if item['is_valid'] else 'warn-chip'}">{validity}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )



def render_upload_page() -> None:
    page_header("Subir archivos")

    col_left, col_right = st.columns([1.05, 1])

    with col_left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="folder-title">📂 Clasificar documentos técnicos</div>', unsafe_allow_html=True)
        
        bank = st.text_input("Banco o cliente", placeholder="Ejemplo: Banco Soluciones del Sur")
        project = st.text_input("Proyecto", placeholder="Ejemplo: Automatización de Procesos Internos")       
        document_type = st.selectbox(
            "Tipo de documento",
            ["", "RFP", "RFP_QA", "MEETING", "TECHNICAL_ANNEX_AS_IS", "TECHNICAL_ANNEX_TO_BE"],
            format_func=lambda x: "Selecciona un tipo de documento" if x == "" else x,
        )
        st.caption("Carpeta final fija: RFP")

    if bank and project:
        target = build_target_path(bank, project)
        st.info(f"Ruta destino: {target}")

    st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)

        st.markdown(
            '<div class="folder-title">📤 Carga de documentos</div>',
            unsafe_allow_html=True
        )

        uploaded_files = st.file_uploader(
            "",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Límite 200 MB por PDF.",
        )

        st.markdown(
            '<div class="tiny-muted">Puedes arrastrar o seleccionar documentos RFP, RFP_QA, MEETING y TECHNICAL_ANNEX de Arquitectura AS-IS / TO-BE.</div>',
            unsafe_allow_html=True,
        )
        
        st.markdown('</div>', unsafe_allow_html=True)


    validations = validate_uploaded_files(uploaded_files)
    st.session_state.last_validation_results = validations

    if validations:
        render_validation_results(validations)

    st.write("")
    action_1, action_2 = st.columns(2)

    with action_1:
        st.markdown('<div class="big-action">', unsafe_allow_html=True)
        if st.button("Subir documento al sistema", use_container_width=True):
            if not bank.strip() or not project.strip():
                st.error("Debes completar Banco o cliente y Proyecto.")
            elif not document_type:
                st.error("Debes seleccionar un tipo de documento.")
            elif not uploaded_files:
                st.error("Debes subir al menos un PDF.")
            else:
                    invalid_items = [v for v in validations if not bool(v["is_valid"])]
                    if invalid_items:
                        st.error("Hay archivos inválidos. Corrige el tipo de archivo o el tamaño antes de guardar.")
                    else:
                        target_dir = ensure_project_structure(bank, project)
                        saved = save_validated_files(validations, target_dir)
                        st.session_state.last_saved_files = [str(p) for p in saved]
                        if saved:
                            st.success(f"Se guardaron {len(saved)} archivo(s) en la carpeta del proyecto.")
                        else:
                            st.warning("No se guardó ningún archivo.")
        st.markdown('</div>', unsafe_allow_html=True)

    with action_2:
        st.markdown('<div class="big-action">', unsafe_allow_html=True)
        if st.button("Generar Graph de los archivos nuevos", use_container_width=True):
            with st.spinner("Ejecutando build_general_kg y build_master_kg..."):
                results = run_build_pipeline(run_general=True, run_master=True)
            st.session_state.last_build_results = results

            all_ok = all(r["success"] for r in results) if results else False
            if all_ok:
                st.success("El pipeline del grafo terminó correctamente.")
            else:
                st.warning("El pipeline terminó con uno o más errores. Revisa los logs.")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.last_saved_files:
        with st.expander("Archivos guardados", expanded=True):
            for item in st.session_state.last_saved_files:
                st.markdown(
                    f"<div style='color:#1b2740; font-weight:600; margin-bottom:6px;'>📄 {item}</div>",
                    unsafe_allow_html=True,
                )

    if st.session_state.last_build_results:
        with st.expander("Resultados de construcción del grafo", expanded=True):
            for result in st.session_state.last_build_results:
                if result["success"]:
                    st.success(result["name"])
                else:
                    st.error(result["name"])
                st.code(result["log"] or "Sin salida")



def render_proposal_page() -> None:
    page_header("Generar propuesta")

    left, right = st.columns([1, 1])

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="folder-title">📂 Buscar información</div>', unsafe_allow_html=True)

        banks = get_available_banks()
        default_bank = st.session_state.last_selected_bank if st.session_state.last_selected_bank in banks else ""

        selected_bank = st.selectbox(
            "Banco",
            options=[""] + banks,
            index=([''] + banks).index(default_bank) if default_bank in ([''] + banks) else 0,
            format_func=lambda x: "Selecciona un banco" if not x else x,
        )

        projects = get_available_projects(selected_bank) if selected_bank else []
        default_project = st.session_state.last_selected_project if st.session_state.last_selected_project in projects else ""

        selected_project = st.selectbox(
            "Proyecto",
            options=[""] + projects,
            index=([''] + projects).index(default_project) if default_project in ([''] + projects) else 0,
            format_func=lambda x: "Selecciona un proyecto" if not x else x,
        )

        st.session_state.last_selected_bank = selected_bank
        st.session_state.last_selected_project = selected_project

        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="folder-title">📂 Consulta propuesta</div>', unsafe_allow_html=True)

        prompt = st.text_area(
            "Construir prompt de propuesta",
            placeholder=(
                "Ejemplo: Necesito una propuesta técnica para el Banco Soluciones del Sur "
                "y el proyecto Automatización de Procesos Internos, enfocada en "
                "automatización, arquitectura empresarial, trazabilidad documental, "
                "AS-IS / TO-BE, seguridad y escalabilidad."
            ),
            height=190,
        )

        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    btn_left, btn_right = st.columns(2)

    with btn_left:
        st.markdown('<div class="big-action">', unsafe_allow_html=True)

        if st.button("Generar propuesta técnica proyecto específico", use_container_width=True):
            if not selected_bank or not selected_project:
                st.error("Debes seleccionar un banco y un proyecto guardados.")
            else:
                with st.spinner("Construyendo contexto y generando propuesta técnica..."):
                    ok, proposal_text, proposal_log = generate_proposal(
                        selected_bank,
                        selected_project,
                        ""
                    )

                st.session_state.last_proposal_text = proposal_text
                st.session_state.last_proposal_log = proposal_log

                if ok:
                    st.success("Propuesta generada correctamente.")
                    if "Workspace ya existente" in proposal_log:
                        st.info("♻️ Se reutilizó un workspace existente.")
                    else:
                        st.info("Se construyó un nuevo contexto del grafo.")
                else:
                    st.error("No se pudo generar la propuesta.")
                    st.markdown("**Mensaje principal:**")
                    st.code(proposal_text)
                    st.markdown("**Detalle técnico / log:**")
                    st.code(proposal_log)

        st.markdown('</div>', unsafe_allow_html=True)

    with btn_right:
        st.markdown('<div class="big-action">', unsafe_allow_html=True)

        if st.button("Generar propuesta técnica con prompt", use_container_width=True):
            if not selected_bank or not selected_project:
                st.error("Debes seleccionar un banco y un proyecto guardados.")
            elif not prompt.strip():
                st.error("Debes escribir un prompt para generar la propuesta.")
            else:
                with st.spinner("Analizando prompt y generando propuesta técnica..."):
                    ok, proposal_text, proposal_log = generate_proposal(
                        selected_bank,
                        selected_project,
                        prompt
                    )

                st.session_state.last_proposal_text = proposal_text
                st.session_state.last_proposal_log = proposal_log

                if ok:
                    st.success("Propuesta generada correctamente.")
                    if "Workspace ya existente" in proposal_log:
                        st.info("♻️ Se reutilizó un workspace existente.")
                    else:
                        st.info("Se construyó un nuevo contexto del grafo.")
                else:
                    st.error("No se pudo generar la propuesta.")
                    st.markdown("**Mensaje principal:**")
                    st.code(proposal_text)
                    st.markdown("**Detalle técnico / log:**")
                    st.code(proposal_log)

        st.markdown('</div>', unsafe_allow_html=True)

    if selected_bank and selected_project:
        files = list_files_for_project(selected_bank, selected_project)

        with st.expander("Archivos encontrados para el proyecto seleccionado", expanded=False):
            if files:
                for file_name in files:
                    detected = detect_document_type(file_name)
                    st.markdown(
                        f"<div style='color:#1b2740; font-weight:600; margin-bottom:6px;'>📄 {file_name} · {detected}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.write("No se encontraron archivos en la carpeta del proyecto.")

    if st.session_state.last_proposal_text:
        st.write("")
        st.subheader("Resultado de propuesta")

        pdf_data = build_proposal_pdf(
            st.session_state.last_proposal_text,
            bank=selected_bank,
            project=selected_project,
        )

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            st.download_button(
                label="📥 Descargar propuesta en PDF",
                data=pdf_data,
                file_name="propuesta_tecnica.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with col_dl2:
            st.download_button(
                label="📄 Descargar propuesta en TXT",
                data=st.session_state.last_proposal_text,
                file_name="propuesta_tecnica.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown(
            f"""
            <div class="proposal-box">
                {st.session_state.last_proposal_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.last_proposal_log:
        with st.expander("Detalle técnico / log", expanded=False):
            st.code(st.session_state.last_proposal_log)



def build_proposal_pdf(text: str, bank: str = "", project: str = "") -> bytes:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=45,
        rightMargin=45,
        topMargin=50,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="ProposalTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=HexColor("#1b2740"),
        spaceAfter=14,
    )

    subtitle_style = ParagraphStyle(
        name="ProposalSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=HexColor("#5b6573"),
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        name="ProposalHeading",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=HexColor("#0f4c81"),
        spaceBefore=12,
        spaceAfter=10,
    )

    body_style = ParagraphStyle(
        name="ProposalBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=HexColor("#1f2937"),
        spaceAfter=6,
    )

    meta_style = ParagraphStyle(
        name="ProposalMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=HexColor("#374151"),
        spaceAfter=4,
    )

    story = []

    title = "Propuesta Técnica Generada"
    if bank or project:
        title = f"Propuesta Técnica - {bank}" if bank else "Propuesta Técnica Generada"

    story.append(Paragraph(title, title_style))

    subtitle_parts = []
    if bank:
        subtitle_parts.append(f"<b>Banco:</b> {bank}")
    if project:
        subtitle_parts.append(f"<b>Proyecto:</b> {project}")
    subtitle_parts.append(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    story.append(Paragraph(" | ".join(subtitle_parts), subtitle_style))
    story.append(Spacer(1, 8))

    for raw_line in text.split("\n"):
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 6))
            continue

        clean_line = clean_markdown(line)

        safe_line = (
            clean_line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

        is_numbered_heading = re.match(r"^\d+\.\s+", line)

        is_short_heading = (
            len(line) < 80
            and ":" not in line
            and not line.startswith("-")
            and not line.startswith("*")
        )

        if is_numbered_heading:
            story.append(Paragraph(f"<b>{safe_line}</b>", heading_style))

        elif is_short_heading:
            story.append(Paragraph(f"<b>{safe_line}</b>", heading_style))

        else:
            if ":" in safe_line and len(safe_line) > 60:
                parts = safe_line.split(":", 1)
                story.append(Paragraph(f"<b>{parts[0]}:</b>{parts[1]}", body_style))
            else:
                story.append(Paragraph(safe_line, body_style))

            

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================================
# APP
# ==========================================================
def main() -> None:
    st.set_page_config(
        page_title="Sistema de soporte a la decisión para preventa técnica",
        page_icon="📘",
        layout="wide",
    )

    inject_custom_css()
    init_state()
    sidebar_navigation()

    if st.session_state.page == "inicio":
        render_home()
    elif st.session_state.page == "subir":
        render_upload_page()
    elif st.session_state.page == "propuesta":
        render_proposal_page()
    else:
        render_home()


if __name__ == "__main__":
    main()

