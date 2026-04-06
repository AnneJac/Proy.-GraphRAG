import typer

from src.phase_2.orchestration.proposal_generator import generate_workspace_proposal

app = typer.Typer(help="Generación de propuesta técnica desde workspace.")


@app.command()
def generate(
    workspace_id: str = typer.Option(..., help="ID del workspace"),
):
    print(f"🚀 Generando propuesta para workspace: {workspace_id}")

    proposal = generate_workspace_proposal(workspace_id)

    print("\n" + "=" * 80)
    print("📄 PROPUESTA GENERADA\n")
    print(proposal)
    print("\n" + "=" * 80)


if __name__ == "__main__":
    app()