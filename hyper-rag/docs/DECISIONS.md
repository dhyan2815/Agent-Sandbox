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

## 7. Retrieval is scored against "information needs", at document level

- **Chosen:** each golden question lists one or more needs; a need is a set of documents, any
  of which contains that part of the answer. Recall@k is the share of needs met in the top k
  chunks. A second metric, facts@5, checks whether the answer's key strings appear in the top
  five chunks.
- **Alternatives:** label individual chunks as relevant; count each listed document separately.
- **Why:** chunk labels break whenever chunk size changes, which is exactly the parameter one
  wants to tune. Counting alternative pages separately punishes a system for finding the answer
  on page A when the label also listed page B. Needs handle both, and multi-part questions get
  one need per part.
- **Cost of the choice:** document-level recall is lenient and saturates quickly (0.98 on the
  payments set for plain vector search). facts@5 is the stricter passage-level check.

## 8. Passages are graded in one batched LLM call, and decisions go to a smaller model

- **Chosen:** one `grade` call returns the numbers of all relevant passages. The agent's
  decision calls (route, grade, rewrite, self-check) use `control_model`; only the answer is
  written by the larger `llm_model`.
- **Alternatives:** grade each passage in its own call (as in the Corrective RAG paper); use one
  model for everything.
- **Why:** Groq's free plan allows 8K tokens per minute and 200K per day per model. Per-passage
  grading multiplies requests by five. Splitting roles across two models gives each its own
  budget, and classification-style decisions do not need the largest model.

## 9. The self-check fails closed

- **Chosen:** an answer is released only when the checker replies `{"grounded": true}`. A
  "false", a malformed reply or a missing field all lead to a refusal.
- **Alternative:** release the answer unless the checker explicitly objects.
- **Why:** the check exists to stop unsupported answers. If it cannot give a clear yes, the safe
  default for a documentation assistant is to decline.
- **Cost of the choice:** measured on the payments set, the agent declines some answerable
  questions that single-shot RAG answers correctly. See the README results.

## 10. Model replies are normalised before anything else reads them

- **Chosen:** `normalise_answer` rewrites model-specific citation marks (for example
  `【1†L9-L12】`) to `[1]` and typographic spaces and hyphens to ASCII.
- **Why:** the first live eval run reported that only 34% of answers had citations and 44%
  contained their key facts. Reading the answers showed the model was citing correctly, in its
  own bracket style, and writing `T + 2` with narrow no-break spaces. The metric was wrong, not
  the system. Normalising once, at the boundary, fixes parsing for every provider.
- **Lesson:** read the raw outputs before trusting a surprising number.

## 11. Ingestion respects robots.txt even when it costs coverage

- **Chosen:** the fetcher checks robots.txt, honours Crawl-delay, keeps a disk copy and retries
  politely on 429. Sources that refuse automated access are left out and documented.
- **What it cost:** npci.org.in (UPI's operator) returns "Access Denied", so UPI is covered
  through Razorpay's pages. The arXiv API host disallows crawlers, so paper metadata comes from
  the abstract pages. Indian government farming portals were unreachable or JavaScript-only, so
  the farming pack reads Wikipedia instead.

## 12. The codebase pack reshapes code into headings instead of adding a code chunker

- **Chosen:** the pack's ingest script uses `ast` to emit each top-level function and class
  under its own markdown heading. The engine's ordinary heading-aware chunker then cuts at
  function boundaries.
- **Alternative:** add a language-aware chunker to the engine.
- **Why:** the rule for this project is that a new domain must not change engine code. The pack
  owns everything domain-specific; the engine only ever sees `Document`s.
