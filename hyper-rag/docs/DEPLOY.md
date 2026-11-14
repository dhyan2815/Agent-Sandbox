# Deploying Hyper-RAG on free tiers

This is the Phase 6 runbook. The recommended setup keeps everything on Hugging Face: one
account, one token, no Cloudflare and no Qdrant (decision 44). The earlier setup, Cloudflare
R2 with Qdrant Cloud, still works and is at the end of this file.

Verify each service's free limits on its own page the day you sign up. The Hugging Face
figures below are from its own docs, read 2026-11-14.

## What runs where

| Piece | Service | Free allowance (verify) | What is stored |
|---|---|---|---|
| App + models + OCR | Hugging Face Space | 2 vCPU, 16 GB RAM, 50 GB disk **wiped on restart** | Nothing that matters |
| Files, parsed pages, vectors, job log | Hugging Face Storage Bucket (private) | 100 GB of private storage per free account | Originals, page units, per-file indexes, SQLite copy |
| Answers | Groq | 30 req/min, 200K tokens/day per model | nothing |

Vectors and the keyword index are not in a database: each file's index is a pair of objects
in the bucket, and the app rebuilds its in-memory search from them at start-up. That holds
every vector in RAM, which is the limit to watch on very large collections (see the end).

**Which Space.** Hugging Face now requires a paid plan (PRO, $9/month) to create a Docker
Space. Two ways to run the app:

- **Free: a Gradio Space on ZeroGPU** (a free account may host two). Template in
  `deploy/gradio-space/`. The entry file runs on a laptop, but it has **not been run on a
  real Space yet**, and it uses a GPU slot for an app that runs on the CPU, which is not what
  ZeroGPU is for. If Hugging Face refuses it, use the next one.
- **PRO: a Docker Space on CPU Basic.** `Dockerfile` and `deploy/docker-space-README.md`.
  This is the tested image.

## 1. Make the account, bucket and keys

1. **Groq:** create a key at <https://console.groq.com/keys>.
2. **Hugging Face token:** Settings, Access Tokens, new token with **write** access.
3. **Bucket:** `hf buckets create hyper-rag --private` (or the Buckets page). Its id is
   `<your username>/hyper-rag`.
4. Pick a long **password** for the app.

## 2. Create the Space

**Free (Gradio):**

1. On your machine: `cd hyper-rag/web && npm ci && npm run build`.
2. New Space, SDK **Gradio**, hardware **ZeroGPU**.
3. Push to the Space repository: the three files in `deploy/gradio-space/` at the top
   level, and from `hyper-rag/`: `config.yaml`, `src/`, `packs/` and `web/dist/`.

**PRO (Docker):**

1. New Space, SDK **Docker**, hardware **CPU Basic**.
2. Copy `deploy/docker-space-README.md` to the Space repository's `README.md`.
3. Push the `hyper-rag/` folder's contents (`Dockerfile`, `pyproject.toml`, `config.yaml`,
   `src/`, `packs/`, `web/`) to the Space repository.

Either way the Space can be Public (the app's own login protects it) or Private.

## 3. Set secrets and variables

On the Space: Settings, Variables and secrets.

**Secrets** (never in `config.yaml`, never committed):

| Name | Value |
|---|---|
| `HYPER_RAG_PASSWORD` | the app password |
| `GROQ_API_KEY` | Groq key |
| `HF_TOKEN` | the write token |

**Variables:**

| Name | Value |
|---|---|
| `HYPER_RAG_EMBEDDER` | `fastembed` |
| `HYPER_RAG_RERANKER` | `fastembed` |
| `HYPER_RAG_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `HYPER_RAG_RERANKER_MODEL` | `Xenova/ms-marco-MiniLM-L-6-v2` |
| `HYPER_RAG_BLOB_STORE` | `hf` |
| `HYPER_RAG_HF_BUCKET` | `<your username>/hyper-rag` |
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
- **Readiness.** `GET /ready` (behind the login) probes the bucket and returns 503 with the
  failing probe's error. Use it to find a wrong token.
- **Restart.** The disk is wiped; files and indexes come back from the bucket and jobs
  resume from their last window. Checked against a real bucket on 2026-11-14 (upload, stop,
  start on an empty disk, a cited answer from Groq) and in `tests/test_hosted_stores.py`.
- **A killed Space** can lose the last two seconds of small writes (they are sent in
  batches). The file being read resumes from the checkpoint that did arrive.
- **One app per bucket.** The app lists the bucket once at start and trusts that list. Do
  not point two running apps, or the CLI and a running app, at the same bucket and prefix.
- **Hourly limit.** Questions, claim checks and LLM exports count toward
  `HYPER_RAG_MODEL_REQUESTS_PER_HOUR` per client address. Over it, the API answers 429 with
  Retry-After and the page shows the message.
- **Memory.** Search holds every chunk vector in RAM (384 floats per chunk, about 1.5 KB).
  A million chunks is about 1.5 GB, inside the Space's 16 GB. Past that, use Qdrant below.

## 5. Smoke test after deploy

1. Open the URL, log in.
2. Create a collection, upload a small PDF, ask a question; the answer should cite a page.
3. Restart the Space (Settings, Factory reboot). Reload: the collection and its answer should
   still be there.
4. `curl -s https://<space>.hf.space/health` returns `{"status":"ok","warm":"ready"}`.

## Alternative: Cloudflare R2 and Qdrant Cloud

The setup from plan v2 phase 2. Vectors live in Qdrant instead of RAM, at the cost of two
more accounts. Not run against the real services.

1. **R2:** create a bucket, then an API token with Object Read & Write for it. The endpoint
   is `https://<account id>.r2.cloudflarestorage.com`.
2. **Qdrant Cloud:** create a free cluster (1 GB RAM, 4 GB disk). Note its URL and make an
   API key. Free clusters may pause after a quiet spell (reported, unverified).
3. Secrets: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (the R2 token) and
   `QDRANT_API_KEY`, in place of `HF_TOKEN`.
4. Variables, in place of the two bucket ones: `HYPER_RAG_BLOB_STORE=s3`,
   `HYPER_RAG_S3_BUCKET`, `HYPER_RAG_S3_ENDPOINT`, `HYPER_RAG_VECTOR_STORE=qdrant`,
   `HYPER_RAG_LEXICAL_STORE=qdrant`, `HYPER_RAG_QDRANT_URL`.
