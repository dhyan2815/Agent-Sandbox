# Hyper-RAG build plan

Agentic RAG over document collections, with citations and a measured evaluation.
Lives in `hyper-rag/` inside the Agent-Sandbox repo; Python package `hyper_rag`.

## Shape of the system

```
packs/<name>/            one folder per domain pack (no engine code in here)
  pack.yaml              sources, chunking and retrieval settings
  ingest.py              fetches sources -> data/<name>/docs.jsonl
  golden.jsonl           questions, reference answers, relevant sources
src/hyper_rag/
  config.py              settings from .env + pack.yaml
  llm/                   one provider interface: fake, groq, gemini
                         + disk cache, retry with backoff, rate limiter
  ingest/                chunking, index building
  retrieval/             dense (local ONNX embeddings), BM25, RRF, reranker
  agent/                 LangGraph: route -> retrieve -> grade -> (rewrite, retry)
                         -> generate with citations -> groundedness self-check
  eval/                  retrieval metrics, answer metrics, ablation, resumable runs
  cli.py, api.py         Typer CLI (ingest, ask, eval) and FastAPI endpoint
data/                    git-ignored: downloaded corpora, indexes, caches
```

The engine discovers packs by listing `packs/`. Adding a pack means adding a
folder; nothing under `src/` changes.

## Choices made up front (details in DECISIONS.md)

| Area | Choice | Why |
|---|---|---|
| Embeddings + reranker | `fastembed` (ONNX Runtime) with small CPU models | No PyTorch install, runs on any laptop, no rate limits |
| Vector index | Exact cosine search over a NumPy matrix | Corpora are a few thousand chunks; exact search is fast and explainable |
| Sparse search | BM25 (`rank-bm25`) | Catches exact identifiers such as API names and error codes |
| Fusion | Reciprocal rank fusion | Needs no score normalisation between dense and BM25 |
| LLM providers | Groq and Gemini over plain HTTPS (`httpx`), no SDKs | One small interface, one retry path, easy to read |
| Models | Groq `openai/gpt-oss-120b` / `openai/gpt-oss-20b`; Gemini `gemini-3.5-flash-lite` / `gemini-3.8-flash` | Listed on the providers' free tiers on 2026-11-10; names live in config only |
| Offline mode | Hashing embedder + rule-based fake LLM + sample corpus written by hand | Tests and CI eval need no key and no network |

Free-tier budget that shapes the design: Groq allows 30 requests/min but only
8K tokens/min and 200K tokens/day per model, so prompts stay small, passages are
graded in one batched call, every LLM response is cached on disk, and eval runs
write one result row per question so they resume after a rate limit.

## Milestones

1. **Skeleton**: project layout, pinned dependencies, ruff, pytest, CI workflow,
   sample pack (hand-written corpus + golden set), fake provider, first test.
2. **Retrieval**: chunking, dense + BM25 + RRF + rerank, payments pack ingestion
   (Razorpay, UPI, Google Wallet), golden set, recall@k / MRR / nDCG.
3. **Agent**: LangGraph graph with routing, grading, rewrite-and-retry (capped),
   cited generation, groundedness self-check that can decline.
4. **Evaluation**: answer metrics (groundedness, citation correctness, answer
   correctness, refusal behaviour), ablation over vector-only, hybrid,
   hybrid + rerank, full agent. Run on the free tier with real keys.
5. **Interfaces**: CLI `ingest`, `ask`, `eval`; FastAPI `/ask`.
6. **More packs**: farming advisories, RAG/agent research papers, GitHub codebase
   Q&A, each with a golden set and eval results.
7. **README**: what it is, architecture diagram, five-minute quickstart, measured
   results with reproduce commands, limitations, next steps.
8. **Optional**: small web UI and a free deployment.

After each milestone: run tests, run the CLI on a real question, run the
relevant eval, commit, push.

## Rules for results

Every number in the README comes from a run that was executed, with its command.
Runs that could not finish are reported as such, not filled in.
