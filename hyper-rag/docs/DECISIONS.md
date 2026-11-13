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

## 13. The router only filters out clearly unrelated questions

- **Chosen:** the routing prompt says to retrieve whenever the question touches the
  collection's subject at all, and to decline only small talk or another field.
- **What it replaced:** "retrieve if the question could plausibly be answered from the
  collection". With that wording the small control model declined 4 of 32 answerable payments
  questions and 7 of 16 farming questions before any search ran.
- **Why:** a wrong "retrieve" costs one local search and a grading call, and grading can still
  decline. A wrong "decline" loses an answerable question with no second chance. The two
  errors are not equally expensive, so the prompt should lean one way.
- **Still open:** the router trusts the pack description. A cheaper and sturdier signal would
  be the reranker's best score for the question.

## 14. Groundedness is judged against the passages an answer cites

- **Chosen:** the eval's groundedness judge sees only the cited passages (all passages if the
  answer cites none).
- **Alternative:** judge against everything that was retrieved.
- **Why:** a claim that is true of passage 3 but cited to passage 1 is a citation error a reader
  would be misled by; judging against cited passages catches it. It also cuts the judge prompt
  by about 60%, which matters when the judge has 200K tokens per day.

## 15. The judge is a different model family, with reasoning switched off

- **Chosen:** `qwen/qwen3.8-27b` judges answers written by `openai/gpt-oss-120b`. Exact-match
  key facts are reported next to the judged correctness as a check on the judge.
- **Why a different model:** a model grading its own output tends to agree with itself.
- **Why no reasoning:** on the free plan the judge is limited to 1,000 output tokens per minute
  and reasoning tokens count as output. A verdict is a few tokens of JSON.

## 16. What the free tier taught about running evals

- Budget tokens per day before designing the eval, not after. Four configurations x 38
  questions x two judged metrics is several hundred calls; at 200K tokens per day per model
  that is most of a day's quota.
- Cache every reply and write one result row per question. This run was stopped by a quota
  four times and never repeated a finished call.
- Separate what needs a judge from what does not. Citations, refusals and exact-match facts are
  deterministic and free; `--no-judge` reports them while the judged metrics wait for quota.

## 17. Every upload format becomes the same markdown units

Each parser (PDF, Word, PowerPoint, Excel, image, text) returns a list of units: a page, a
slide, a sheet or a section, each as markdown with `#` headings and pipe tables. Alternatives:
a document-parsing framework (unstructured, docling), or a layout model. Those handle more
edge cases but pull in PyTorch and model downloads, which the laptop constraint and the
"install in a minute" goal rule out. One library per format (pdfplumber, python-docx,
python-pptx, openpyxl) is small, readable and easy to explain. The cost is on hard layouts:
borderless tables and three-column pages are not recovered.

## 18. OCR with RapidOCR, and no vision model

RapidOCR runs PaddleOCR's small models through ONNX Runtime, which fastembed already
installs, and ships its models inside the wheel. Tesseract needs a system binary, the usual
way OCR setups break on Windows. EasyOCR needs PyTorch. A vision model would describe charts
and photos, which OCR cannot, but it sends every image to a provider and spends the free
daily quota; the user chose local only. A PDF page with almost no text layer is rendered
and read whole; otherwise each embedded image is cropped and read on its own.

## 19. Tables are split by rows with the header repeated

A long sheet becomes many chunks. Cutting at a character count leaves chunks that are rows
of numbers with no column names, useless to the retriever and to the model. Splitting between
rows and repeating the header keeps each chunk readable alone. It is opt-in
(`structured=True`) and only uploads use it, so the chunks behind the published pack results
did not change. Known gap: 1,200 characters of numbers can exceed the embedding model's 512
tokens, so the vector for a dense table chunk may only cover its first part; BM25 sees all
of it.

## 20. One index per file inside a collection

Adding a file embeds only that file; removing one deletes a folder; the collection's
retriever stacks the per-file matrices at load time. A single index per collection would need
rewriting on every change. Each unit is a `Document`, so a citation resolves to a page, slide
or sheet with no change to the retriever or the agent. Uploading a file with an existing name
replaces it; identical bytes are detected by hash and skipped.

## 21. Uploaded collections skip the router

Decision 13 kept the router as a cheap filter that reads a hand-written pack description. A
collection has no such description, so one is assembled from file names and headings. In the
first live run the router used it to decline "How much is the site survey fee?", whose answer
was on a scanned page with no heading. Collections now go straight to retrieval and let
grading decide. Declining an out-of-scope question costs about six calls instead of one. The
reranker's top score as a free scope signal (already on the to-do list) is the better fix.

## 22. Answers are shown after the self-check, not streamed token by token

The UI streams the agent's steps as they finish (searching, grading, writing, checking) and
shows the answer once the groundedness check has passed. Streaming tokens would feel faster,
but the check can still reject the draft, and showing text that is then withdrawn is worse
than a few seconds of waiting. It would also show the model's raw citation format before it
is normalised.

## 23. Auto-evaluation: generated questions, strict about what they prove

Nobody writes a golden set for files they just uploaded, so the generator model writes one
question per sampled passage (spread over files, fixed seed) and the normal harness runs on
it. Limits, stated in the UI and the README: questions share their passage's wording, so
retrieval looks better than it is; there are no unanswerable questions; the exact-match
"fact" is kept only if it is at most four words and really occurs in the passage, after the
first run showed whole sentences being used as facts. The judge is off by default because it
doubles the calls on a free tier.

## 24. Upload safety for a local, single-user tool

The API has no authentication and says so. Within that: collection ids are slugs checked
before touching the file system, stored files are named by content hash, not by the uploaded
name, uploads have a size limit and an extension allow-list, and only PDFs and images are
served inline. Every other upload is sent back as a download, so an uploaded HTML file is
never rendered as a page of the app. The UI builds every node with `textContent`.
