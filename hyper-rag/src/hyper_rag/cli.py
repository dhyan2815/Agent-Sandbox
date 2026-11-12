"""Command line interface.

hyper-rag ingest | ask | eval ...        the built-in domain packs
hyper-rag collection create | add | list | report | ask | eval | remove | delete
                                         your own uploaded documents
"""

import json
from pathlib import Path

import typer

from hyper_rag.config import load_settings
from hyper_rag.packs import list_packs, load_golden, load_pack

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Agentic RAG with citations.")

collection_app = typer.Typer(no_args_is_help=True, help="Upload your own documents and ask them.")
app.add_typer(collection_app, name="collection")

OFFLINE_HELP = "No network, no API key: fake LLM, hashing embedder, lexical reranker."


def _print_table(rows: list[dict]) -> None:
    """Print dict rows as a GitHub-flavoured markdown table (pastes straight into a README)."""
    columns = list(rows[0])
    typer.echo("| " + " | ".join(columns) + " |")
    typer.echo("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        typer.echo("| " + " | ".join(str(row[c]) for c in columns) + " |")


def _print_answer(answer, trace: bool) -> None:
    typer.echo(answer.text)
    if answer.citations:
        typer.echo("\nSources:")
        for number, chunk in answer.citations:
            typer.echo(f"  [{number}] {chunk.title}\n      {chunk.url}")
    if trace:
        typer.echo("\nTrace:")
        for step in answer.trace:
            typer.echo(f"  {step}")


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


@app.command()
def ask(
    pack: str,
    question: str,
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
    trace: bool = typer.Option(False, "--trace", help="Show each step the agent took."),
    as_json: bool = typer.Option(False, "--json", help="Print the full result as JSON."),
) -> None:
    """Ask the agent a question about a pack. Answers cite their sources as [n]."""
    from hyper_rag.service import build_agent

    answer = build_agent(pack, load_settings(offline)).ask(question)
    if as_json:
        typer.echo(json.dumps(answer.to_dict(), indent=2, ensure_ascii=False))
        return
    _print_answer(answer, trace)


@app.command("eval")
def eval_answers(
    pack: str,
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
    save: bool = typer.Option(False, "--save", help="Also write results/<pack>-<run>.json."),
    no_judge: bool = typer.Option(
        False, "--no-judge", help="Skip the LLM-judged metrics (groundedness, correctness)."
    ),
    configs: str = typer.Option(
        "vector,hybrid,hybrid_rerank,agent",
        "--configs",
        help="Comma-separated configurations to answer with (fewer = fewer LLM calls).",
    ),
) -> None:
    """Full evaluation: retrieval metrics, then the answer-quality ablation.

    Resumable: if a rate limit stops the run, run the same command again.
    """
    from datetime import date
    from pathlib import Path

    from hyper_rag.evaluation.answer_eval import run_answer_eval
    from hyper_rag.evaluation.retrieval_eval import evaluate_retrieval
    from hyper_rag.index import load_retriever, pack_data_dir
    from hyper_rag.llm import LLMError, build_llm

    settings = load_settings(offline)
    loaded = load_pack(settings.packs_dir, pack)
    golden = load_golden(loaded)
    retriever = load_retriever(loaded, settings)
    generator = build_llm(settings, "generator")
    control = build_llm(settings, "control")
    judge = None if no_judge else build_llm(settings, "judge")
    judge_name = judge.name if judge else "none"

    typer.echo(f"Retrieval ({len(golden)} golden questions, embedder {retriever.embedder.name})\n")
    retrieval_rows = evaluate_retrieval(retriever, golden)
    _print_table(retrieval_rows)

    # The run folder is named after generator and judge, so runs never mix their rows.
    run_name = "offline" if offline else f"{generator.name}__judge-{judge_name}"
    run_name = run_name.replace("/", "-").replace(":", "-")
    run_dir = pack_data_dir(settings, pack) / "eval" / run_name
    typer.echo(f"\nAnswers (generator {generator.name}, judge {judge_name})")
    try:
        answer_rows = run_answer_eval(
            loaded.config.description,
            golden,
            retriever,
            generator,
            control,
            judge,
            settings,
            run_dir,
            configs=tuple(configs.split(",")),
            # Live runs take minutes; show progress. Offline runs finish instantly.
            on_progress=(lambda line: None) if offline else typer.echo,
        )
    except LLMError as error:
        typer.echo(f"\nStopped: {error}\nProgress is saved in {run_dir}. Re-run to continue.")
        raise typer.Exit(code=1) from error
    typer.echo("")
    _print_table(answer_rows)

    if save:
        report = {
            "pack": pack,
            "date": date.today().isoformat(),
            "command": f"hyper-rag eval {pack}"
            + (" --offline" if offline else "")
            + (" --no-judge" if no_judge else "")
            + (f" --configs {configs}" if configs != "vector,hybrid,hybrid_rerank,agent" else ""),
            "generator": generator.name,
            "control": control.name,
            "judge": judge_name,
            "embedder": retriever.embedder.name,
            "reranker": settings.reranker_model if settings.reranker == "fastembed" else "lexical",
            "chunks": len(retriever.chunks),
            "questions": len(golden),
            "retrieval": retrieval_rows,
            "answers": answer_rows,
        }
        out = Path("results") / f"{pack}-{run_name}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        typer.echo(f"\nSaved {out}")


@app.command()
def report() -> None:
    """Print every saved eval in results/ as markdown tables (the README tables come from this)."""
    from pathlib import Path

    for path in sorted(Path("results").glob("*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        typer.echo(f"\n### {saved['pack']} ({path.name})\n")
        typer.echo(
            f"{saved['date']} | `{saved['command']}` | generator `{saved['generator']}` | "
            f"judge `{saved['judge']}` | {saved['chunks']} chunks, {saved['questions']} questions\n"
        )
        _print_table(saved["retrieval"])
        typer.echo("")
        _print_table(saved["answers"])


# --- collections of uploaded documents ----------------------------------------------------


def _store(offline: bool):
    from hyper_rag.uploads import CollectionStore

    settings = load_settings(offline)
    return CollectionStore(settings), settings


def _fail(error: Exception) -> typer.Exit:
    typer.echo(f"Error: {error}", err=True)
    return typer.Exit(code=1)


def _report_row(record: dict) -> dict:
    report = record["report"]
    return {
        "file": record["name"],
        "type": report["kind"],
        "units": f"{report['units']} {report['unit_name']}(s)",
        "tables": report["tables"],
        "images (with text)": f"{report['images']} ({report['images_with_text']})",
        "read by OCR": report["ocr_units"],
        "chunks": record["chunks"],
        "seconds": record["seconds"],
    }


@collection_app.command("create")
def collection_create(
    name: str,
    description: str = typer.Option("", "--description", "-d", help="What the documents are."),
) -> None:
    """Create an empty collection. Its id (shown in the reply) is used by the other commands."""
    from hyper_rag.uploads import CollectionError

    store, _ = _store(offline=True)  # creating a folder needs no models
    try:
        meta = store.create(name, description)
    except CollectionError as error:
        raise _fail(error) from error
    typer.echo(f"Created collection '{meta['name']}' (id: {meta['slug']})")


@collection_app.command("list")
def collection_list() -> None:
    """List collections and how many files each holds."""
    store, _ = _store(offline=True)
    for meta in store.all():
        typer.echo(f"{meta['slug']}: {meta['name']} ({len(meta['files'])} files)")


@collection_app.command("add")
def collection_add(
    collection: str,
    files: list[Path] = typer.Argument(..., exists=True, dir_okay=False, readable=True),  # noqa: B008
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
) -> None:
    """Parse and index files into a collection, then print what was extracted from each."""
    from hyper_rag.uploads import CollectionError

    store, _ = _store(offline)
    rows, failed = [], False
    for path in files:
        try:
            record = store.add_file(collection, path.name, path.read_bytes())
        except CollectionError as error:
            typer.echo(f"Skipped {path.name}: {error}", err=True)
            failed = True
            continue
        if record.get("duplicate"):
            typer.echo(f"Skipped {path.name}: identical to '{record['name']}', already there.")
            continue
        rows.append(_report_row(record))
        for warning in record["report"]["warnings"]:
            typer.echo(f"  {path.name}: {warning}")
    if rows:
        _print_table(rows)
    if failed:
        raise typer.Exit(code=1)


@collection_app.command("report")
def collection_report(collection: str) -> None:
    """The parse report of every file: what was extracted, and what was not."""
    from hyper_rag.uploads import CollectionError

    store, _ = _store(offline=True)
    try:
        meta = store.get(collection)
    except CollectionError as error:
        raise _fail(error) from error
    if not meta["files"]:
        typer.echo("No files yet. Add some: hyper-rag collection add " + collection + " FILE...")
        return
    _print_table([{"id": r["id"], **_report_row(r)} for r in meta["files"]])
    for record in meta["files"]:
        for warning in record["report"]["warnings"]:
            typer.echo(f"  {record['name']}: {warning}")


@collection_app.command("remove")
def collection_remove(collection: str, file_id: str) -> None:
    """Remove one file (by the id shown in `collection report`) from a collection."""
    from hyper_rag.uploads import CollectionError

    store, _ = _store(offline=True)
    try:
        name = store.file_record(collection, file_id)["name"]
        store.remove_file(collection, file_id)
    except CollectionError as error:
        raise _fail(error) from error
    typer.echo(f"Removed {name}")


@collection_app.command("delete")
def collection_delete(
    collection: str,
    yes: bool = typer.Option(False, "--yes", help="Do not ask for confirmation."),
) -> None:
    """Delete a collection and every file uploaded to it."""
    from hyper_rag.uploads import CollectionError

    store, _ = _store(offline=True)
    try:
        meta = store.get(collection)
        if not yes:
            typer.confirm(
                f"Delete '{meta['name']}' and its {len(meta['files'])} files?", abort=True
            )
        store.delete(collection)
    except CollectionError as error:
        raise _fail(error) from error
    typer.echo(f"Deleted {meta['name']}")


@collection_app.command("ask")
def collection_ask(
    collection: str,
    question: str,
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
    trace: bool = typer.Option(False, "--trace", help="Show each step the agent took."),
    as_json: bool = typer.Option(False, "--json", help="Print the full result as JSON."),
) -> None:
    """Ask a question about a collection's documents. Answers cite page, slide or sheet."""
    from hyper_rag.agent import Agent
    from hyper_rag.llm import LLMError, build_llm
    from hyper_rag.uploads import CollectionError

    store, settings = _store(offline)
    try:
        agent = Agent(
            retriever=store.retriever(collection),
            llm=build_llm(settings, "generator"),
            pack_description=store.description(collection),
            max_rewrites=settings.max_rewrites,
            control_llm=build_llm(settings, "control"),
        )
        answer = agent.ask(question)
    except (CollectionError, LLMError) as error:
        raise _fail(error) from error
    if as_json:
        typer.echo(json.dumps(answer.to_dict(), indent=2, ensure_ascii=False))
        return
    _print_answer(answer, trace)


@collection_app.command("eval")
def collection_eval(
    collection: str,
    questions: int = typer.Option(8, "--questions", "-n", help="Test questions to write."),
    judge: bool = typer.Option(False, "--judge", help="Also run the LLM-judged metrics."),
    configs: str = typer.Option("hybrid_rerank,agent", "--configs"),
    regenerate: bool = typer.Option(False, "--regenerate", help="Write new test questions."),
    offline: bool = typer.Option(False, "--offline", help=OFFLINE_HELP),
) -> None:
    """Write test questions from the collection's own passages and score the system on them.

    The questions are easier than real ones (each is written from the passage it is scored
    against), so read the result as a health check of this collection, not a benchmark.
    """
    from hyper_rag.evaluation.synthetic import evaluate_collection
    from hyper_rag.llm import LLMError
    from hyper_rag.uploads import CollectionError

    store, settings = _store(offline)
    try:
        report = evaluate_collection(
            store,
            collection,
            settings,
            questions=questions,
            configs=tuple(configs.split(",")),
            use_judge=judge,
            regenerate=regenerate,
            on_progress=typer.echo,
        )
    except (CollectionError, LLMError, RuntimeError) as error:
        typer.echo("Finished rows are saved; run the same command again to continue.", err=True)
        raise _fail(error) from error
    typer.echo(f"\nRetrieval ({report['questions']} generated questions)\n")
    _print_table(report["retrieval"])
    typer.echo(f"\nAnswers (generator {report['generator']}, judge {report['judge']})\n")
    _print_table(report["answers"])


if __name__ == "__main__":
    app()
