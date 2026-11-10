# Design decisions

One entry per significant choice: what was chosen, what else was considered, and why.
Newest entries are at the bottom.

## 1. Embeddings and reranking run on ONNX Runtime through `fastembed`, not PyTorch

- **Chosen:** `fastembed` with `BAAI/bge-small-en-v1.5` (dense) and a MiniLM cross-encoder (rerank).
- **Alternatives:** `sentence-transformers` on PyTorch; an embeddings API.
- **Why:** The default PyTorch wheel on Linux pulls in gigabytes of CUDA libraries, which makes
  the install slow and the "quickstart in five minutes" promise false. ONNX Runtime is a small
  CPU-only install and the same models run at similar speed on CPU. An embeddings API would add
  cost, rate limits and a network dependency to every query.
- **Cost of the choice:** only models that have an ONNX export in fastembed's catalogue can be used.

## 2. LLM providers are called over plain HTTPS, without their SDKs

- **Chosen:** one `LLM` protocol with a single method, `complete(prompt) -> str`, and
  `httpx` calls to Groq (OpenAI-compatible chat API) and Gemini (`generateContent`).
- **Alternatives:** the `groq` and `google-genai` SDKs; LangChain chat model wrappers.
- **Why:** The system needs exactly one capability from a provider: text in, text out. Calling
  the REST endpoints directly keeps retry, backoff and caching in one place that I wrote and can
  explain, and swapping providers is a config change. SDKs would add two dependency trees for
  features this project does not use (streaming, tools, multimodal).

## 3. Offline mode is a first-class configuration, not a set of mocks

- **Chosen:** a rule-based `FakeLLM`, a feature-hashing embedder and a word-overlap reranker
  that implement the same interfaces as the real components. `Settings.offline()` switches all
  three.
- **Alternatives:** `unittest.mock` patches in each test; recorded HTTP cassettes.
- **Why:** CI must run the tests and an end-to-end eval with no key and no network. Real
  implementations of the interfaces let the whole pipeline run (ingest, retrieve, agent, eval)
  instead of testing pieces against mocks. Cassettes would go stale whenever a prompt changes.
- **Cost of the choice:** offline numbers measure the plumbing, not answer quality. The README
  labels them as such and never mixes them with real-model results.

## 4. Domain packs are folders discovered at run time

- **Chosen:** `packs/<name>/` holds `pack.yaml`, `ingest.py` and `golden.jsonl`. The engine lists
  the folder and loads `ingest.py` with `importlib`. The script's only contract is
  `fetch(pack, raw_dir) -> Iterable[Document]`.
- **Alternatives:** a registry dict in engine code; Python entry points.
- **Why:** Adding a domain must not touch engine code. Everything domain-specific (where the
  sources are, how to clean them) lives in the pack's script; everything after `Document`
  (chunking, indexing, retrieval, agent, eval) is shared.

## 5. Model names live in `config.yaml`, with the date they were checked

- **Chosen:** provider and model names are config values; code never names a model.
- **Why:** Free-tier line-ups change every few months. On 2026-11-10 Groq's free plan listed
  `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b`; older Llama models
  that many tutorials hardcode were no longer on the free list.

## 6. The generator signals "no answer" with a fixed token

- **Chosen:** the generation prompt tells the model to reply `INSUFFICIENT_CONTEXT` when the
  passages do not contain the answer. The agent maps that token to a refusal.
- **Alternatives:** detect refusals by matching phrases such as "I don't know"; a separate
  classifier call.
- **Why:** Refusal behaviour is one of the evaluated metrics, so it has to be detected exactly.
  Phrase matching misses paraphrases, and an extra call costs rate-limit budget.
