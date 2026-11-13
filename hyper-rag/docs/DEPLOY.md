# Deploying Hyper-RAG on free tiers

This is the Phase 6 runbook. Everything here is a checklist you run on your own accounts: the
code needs no change, and none of the steps below can be done from a build session.

Verify each service's free limits on its own page the day you sign up. They change, and the
numbers in this file are from a 2026-11 reading of third-party summaries, not from contracts.

## What runs where

| Piece | Service | Free allowance (verify) | What is stored |
|---|---|---|---|
| App + models + OCR | Hugging Face Space, Docker SDK, CPU Basic | 2 vCPU, 16 GB RAM, 50 GB disk **wiped on restart** | Nothing that matters |
| Files, parsed pages, job log | Cloudflare R2 | 10 GB, free egress | Originals, page units, SQLite copy |
| Vectors and keyword index | Qdrant Cloud | 1 GB RAM, 4 GB disk, one node | int8 vectors + BM25 sparse |
| Answers | Groq | 30 req/min, 200K tokens/day per model | nothing |

Before anything else, confirm the Space tier is still free for your account (forum threads in
2026 report changes). If it is not, the fallback in `PLAN-v2-scale-visuals-features.md`
section 5 applies: ingestion moves to the browser (A10).

## 1. Make the accounts and keys

1. **Groq:** create a key at <https://console.groq.com/keys>.
2. **R2:** create a bucket (for example `hyper-rag`), then an API token with Object Read & Write
   for that bucket. Note the account id for the endpoint
   `https://<account id>.r2.cloudflarestorage.com`.
3. **Qdrant Cloud:** create a free cluster. Note its URL and make an API key.
4. Pick a long **password** for the app.

## 2. Create the Space

1. New Space, SDK **Docker**, hardware **CPU Basic**, visibility **Public** (the app's own
   login protects it) or Private.
2. Copy `deploy/hf-space-README.md` to the Space repository's `README.md` (its front matter
   sets the Docker SDK and port 7860).
3. Push the `hyper-rag/` folder's contents (`Dockerfile`, `pyproject.toml`, `config.yaml`,
   `src/`, `packs/`, `web/`) to the Space repository.

## 3. Set secrets and variables

On the Space: Settings, Variables and secrets.

**Secrets** (never in `config.yaml`, never committed):

| Name | Value |
|---|---|
| `HYPER_RAG_PASSWORD` | the app password |
| `GROQ_API_KEY` | Groq key |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | the R2 token |
| `QDRANT_API_KEY` | Qdrant key |

**Variables:**

| Name | Value |
|---|---|
| `HYPER_RAG_EMBEDDER` | `fastembed` |
| `HYPER_RAG_RERANKER` | `fastembed` |
| `HYPER_RAG_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `HYPER_RAG_RERANKER_MODEL` | `Xenova/ms-marco-MiniLM-L-6-v2` |
| `HYPER_RAG_BLOB_STORE` | `s3` |
| `HYPER_RAG_S3_BUCKET` | your bucket |
| `HYPER_RAG_S3_ENDPOINT` | the R2 endpoint |
| `HYPER_RAG_VECTOR_STORE` | `qdrant` |
| `HYPER_RAG_LEXICAL_STORE` | `qdrant` |
| `HYPER_RAG_QDRANT_URL` | the cluster URL |
| `HYPER_RAG_MODEL_REQUESTS_PER_HOUR` | `120` (the default; lower it to stretch the Groq day) |

Check the same values on your machine first, before pushing:

```bash
hyper-rag doctor --hosted      # exits 1 on an error, prints warnings
```

The app runs the same check at start-up and writes every problem to its log.

## 4. What to expect

- **Cold start.** A sleeping Space takes tens of seconds to wake, then loads about 210 MB of
  models. The page shows "Waking up the server" while it cannot be reached, and a banner
  while the models load. `GET /health` is open and reports `warm: warming | ready`.
- **Readiness.** `GET /ready` (behind the login) probes R2 and Qdrant and returns 503 with
  the failing probe's error. Use it to find a wrong key.
- **Restart.** The disk is wiped; files come back from R2, vectors are in Qdrant, jobs resume
  from their last window. This is tested (`tests/test_hosted_stores.py`), against local
  stand-ins, not against the real services.
- **Hourly limit.** Questions, claim checks and LLM exports count toward
  `HYPER_RAG_MODEL_REQUESTS_PER_HOUR` per client address. Over it, the API answers 429 with
  Retry-After and the page shows the message.
- **Qdrant free clusters** may pause after a quiet spell (reported, unverified). The first
  request after a pause can fail; the error is shown as is.

## 5. Smoke test after deploy

1. Open the URL, log in.
2. Create a collection, upload a small PDF, ask a question; the answer should cite a page.
3. Restart the Space (Settings, Factory reboot). Reload: the collection and its answer should
   still be there.
4. `curl -s https://<space>.hf.space/health` returns `{"status":"ok","warm":"ready"}`.
