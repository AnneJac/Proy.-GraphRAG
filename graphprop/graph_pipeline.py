import typer

from scripts.phase_1.build_master_kg import build_master_kg
from scripts.phase_1.build_general_kg import build_general_kg
from scripts.phase_2.build_workspace import build_workspace
from scripts.phase_2.generate_proposal import generate_proposal

app = typer.Typer(
    name="graph-pipeline",
    help="Pipeline GraphRAG para Fase 1 y Fase 2",
    add_completion=False,
)


@app.command("build-master-kg")
def build_master_kg_cmd():
    build_master_kg()


@app.command("build-general-kg")
def build_general_kg_cmd(
    source_dir: str = typer.Option("output", "--source-dir", "-s"),
):
    build_general_kg(source_dir)


@app.command("build-workspace")
def build_workspace_cmd(
    requirement_text: str = typer.Option(..., "--requirement-text", "-r"),
    workspace_id: str = typer.Option("WS-001", "--workspace-id", "-w"),
    preferred_doc_types: str = typer.Option("", "--preferred-doc-types", "-d"),
    preferred_arch_state: str = typer.Option("", "--preferred-arch-state", "-a"),
):
    doc_types = [x.strip() for x in preferred_doc_types.split(",") if x.strip()]
    arch_state = preferred_arch_state.strip() or None
    build_workspace(requirement_text, workspace_id, doc_types, arch_state)


@app.command("generate-proposal")
def generate_proposal_cmd(
    workspace_id: str = typer.Option(..., "--workspace-id", "-w"),
):
    generate_proposal(workspace_id)


if __name__ == "__main__":
    app()