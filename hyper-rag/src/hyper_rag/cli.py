"""Command line interface: hyper-rag ingest | ask | eval."""

import json

import typer

from hyper_rag.config import load_settings
from hyper_rag.packs import list_packs, load_golden, load_pack

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Agentic RAG with citations.")

OFFLINE_HELP = "No network, no API key: fake LLM, hashing embedder, lexical reranker."


def _print_table(rows: list[dict]) -> None:
    """Print dict rows as a GitHub-flavoured markdown table (pastes straight into a README)."""
    columns = list(rows[0])
    typer.echo("| " + " | ".join(columns) + " |")
    typer.echo("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        typer.echo("| " + " | ".join(str(row[c]) for c in columns) + " |")


@app.command()
def packs() -> None:
    """List the available domain packs."""
    settings = load_settings()
    for name in list_packs(settings.packs_dir):
        typer.echo(f"{name}: {load_pack(settings.packs_dir, name).config.description}")


@app.command()
def ingest(
    pack: str,
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
) -> None:
    """Fetch a pack's sources, chunk them and build its index."""
    from hyper_rag.index import ingest_pack

    settings = load_settings(offline)
    typer.echo(json.dumps(ingest_pack(load_pack(settings.packs_dir, pack), settings), indent=2))


@app.command("eval-retrieval")
def eval_retrieval(
    pack: str,
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
) -> None:
    """Retrieval metrics on the pack's golden set, per retrieval mode. Uses no LLM."""
    from hyper_rag.evaluation.retrieval_eval import evaluate_retrieval
    from hyper_rag.index import load_retriever

    settings = load_settings(offline)
    loaded = load_pack(settings.packs_dir, pack)
    _print_table(evaluate_retrieval(load_retriever(loaded, settings), load_golden(loaded)))


if __name__ == "__main__":
    app()
