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

## 25. Typed events alongside the trace, carried in the run's config

Plan v2 (B0) needs every stage to report what it did with the real objects, so the
visualizer animates actual work. The retriever and every agent node now emit typed events
("r.dense", "a.grade", ...) with ranked chunk ids, scores and milliseconds. The trace lines
stay: the current UI, the CLI and the eval reports read them.

The listener is passed through LangGraph's per-run `config`, not stored on the agent,
because a pack's agent is cached and shared by concurrent requests; a listener on `self`
would mix two users' events. Nodes run inside `graph.stream`, so a plain list collects each
node's events and `ask_events` yields them after the node, before its trace line. With no
listener nothing is emitted, and the offline eval output is byte-identical to before.

Each collection answer's events are saved with the answer (`runs/<id>.json`, the newest 50
kept), which is what makes replay cheap later.

## 26. Token and quota numbers travel with the reply

Providers that know their usage implement `complete_with_usage`, returning the reply and
a dict (tokens in and out, a cache hit flag, rate-limit counters). Usage is returned with the
reply instead of kept as `llm.last_usage`, because one LLM object serves several requests at
once. The plan proposed a `tokens_left_today` meter. A live call to Groq on 2026-11-13
showed its headers carry requests per day (`x-ratelimit-*-requests`, 1000) and tokens per
minute (`x-ratelimit-*-tokens`, 8000) only, so the `llm.quota` event reports those, named
for what they count. A daily token meter would have to be counted locally.

## 27. Storage behind four interfaces, local implementations first

`BlobStore`, `VectorStore`, `LexicalStore` and `JobStore` (`hyper_rag/stores/`) have the
current behaviour as their only implementations: a folder, an exact numpy scan, rank_bm25,
SQLite. Collections now go through them, so R2 and Qdrant can be added in phase 2 without
touching the upload code. The vector and keyword stores are namespaced per collection and
embedding model and change a whole file at a time, which is how uploads change a collection
and how Qdrant will want it; the retriever still works with positions in its chunk list, and
a small adapter maps chunk ids to positions.

Checked before and after: the offline pack eval output is identical, and on a collection of
all nine supported formats the top-10 ids and scores of 18 query and mode pairs are
identical. The packs keep their own on-disk index (`hyper_rag.index`): they are evaluation
corpora built by a command, and their published numbers must not move. The auto-eval's
working files still live in the collection's local folder; they move with phase 2.

Evaluation jobs moved from a dict in memory to the job store. A restart used to forget a
running evaluation; now it reports it as interrupted. Ingestion jobs and their page windows
(plan v2, A3) are phase 1.

## 28. One password and a signed cookie, off unless a password is set

The plan's answer for phase 0 was single-user auth. A password from `HYPER_RAG_PASSWORD`
was chosen over a magic link because a link needs an email service and its key on a free
tier. With no password set nothing changes, so local use and the tests behave as before.

The cookie is `<expiry>.<HMAC-SHA256>` keyed by a hash of the password: no second secret to
manage, and changing the password logs every browser out. It is HttpOnly, `SameSite=Lax`
(other sites' form posts arrive without it, which covers CSRF for this app) and Secure when
the request came over HTTPS, read from `X-Forwarded-Proto` behind a host's proxy. API calls
without a session get 401, pages redirect to `/login`, and `/health` stays open for the
host's probe. Five wrong passwords from one address in 15 minutes block that address for
the rest of the window. Behind a proxy that address is the proxy's unless uvicorn runs with
`--proxy-headers`, in which case the limit becomes global; for one user that is acceptable.
Lax cookies are not sent inside a cross-site iframe, so the app is opened at its own URL
(on Hugging Face, the `*.hf.space` address), not embedded in the Space page.

## 29. The React app is built, not committed, and the classic page stays as a fallback

Phase 0's other half: `web/` is React 19 + Vite + TypeScript with TanStack Query for server
state, the stack plan v2 names for the visualizer. It reproduces the classic page's flows and
look (the stylesheet is copied verbatim), and adds nothing new yet: the event stream is
there for phase 3, but nothing on screen uses it.

The build output is not committed (the user's choice): the Dockerfile and CI build it. So
that `pip install` alone still gives a working app, `/` serves `web/dist/index.html` when it
exists and the classic page otherwise; the classic page also stays at `/classic` until the
React app has replaced it everywhere. Assets are served by a route that refuses any name
resolving outside `web/dist/assets`, with a year-long immutable cache (names carry a hash).

Checked: a Playwright script (`web/e2e/flows.mjs`, also run in CI) logs in, creates a
collection, uploads, asks, follows up, opens a citation, runs the evaluation, asks a pack,
removes a file, deletes the collection and logs out. It passed against uvicorn and against
the Docker image running as user 1000. Screenshots of the two pages answering the same
question match, and the app has no horizontal scroll at 390 px.

Unit tests cover only the pure parts (the SSE reader, the answer parser) with vitest in
Node. jsdom and Testing Library were dropped: npm 10 crashed resolving vitest's optional
peers with them, and the browser script covers the components better. The lockfile is
written by the npm in `node:24` (11.19.1, recorded as `packageManager`); an older npm 11
left out optional packages and `npm ci` in the image refused the lockfile, which the Docker
build caught before CI would have.


## 30. Big files: an X-ray pass, then windows of 32 pages, each a checkpoint

Plan v2 phase 1. Every PDF is first X-rayed with pypdfium2 (`parsing/xray.py`): per page,
the text layer's size, the share covered by large images, vector paths (a table hint), a
two-column test and a content hash. Nothing is rendered and no image is decoded, so the
pass costs milliseconds per page even on a scanned book. Each page gets a route: simple
pages are read from pdfium's text objects (line positions and font sizes, so headings
survive); pages with ruled lines, two columns, images over 1% of the page or no text layer
go to the existing pdfplumber parser; blank pages and exact copies are skipped. The tests
on the original fixtures pass unchanged with these routes.

Running headers and footers are found by position (top or bottom tenth of the page) and
removed only if they repeat word for word on most pages, or are short and numbered like
the pages ("Page 12 of 900"). The first version blanked every number and matched any line
in the margin; on a test file it deleted "Plate 7" and "Fact 7: ..." from every page,
because those have the same shape everywhere. A test now keeps them.

Reading then goes 32 pages at a time: parse, chunk, embed, write the window's units and
index, register it with the search stores. The window's chunk file is written last and is
the checkpoint: a resumed job skips every window that has one, and search sees a window the
moment it is written. Units are stored per window, so a citation on page 900 reads one
window, not the book. The store's lock now only covers metadata writes; parsing and
embedding run outside it, so questions and other uploads never wait for a big file (a test
holds a book mid-window and asks a question meanwhile).

The 300-page cap is gone. Budgets replace it: 2 GB per file, 9 GB of originals and 20,000
pages per collection, all settings. Uploading a file with an existing name keeps the old
one searchable until the new one is ready.

## 31. Resumable uploads through the API, and jobs that resume at start-up

The plan's option 2 (parts through the API) was built rather than direct-to-R2, because R2
comes with phase 2 and the API path works on any host. The protocol is three calls, not tus:
start (name, size: checked against types and budgets before a byte is sent), PUT each 8 MB
part at its offset (a wrong offset gets 409 with the right one, which is how a client
resumes), complete. Parts are appended to a file on disk; the server never holds more than
one part. The direct upload endpoint also stopped reading whole files into memory.

Ingestion runs on a thread pool. At start-up, every file listed as queued or reading is
picked up again and continues from its last committed window: the state that matters is
the files and their checkpoints, not a job queue, so nothing extra has to survive a
restart. Windows can be parsed in worker processes (`ingest_processes`), which also avoids
pdfium's lack of thread safety; in-process, every pdfium call holds one lock, including
the page preview endpoint.

Answers given while a file is still being read carry `reading` (which files, how many
pages searched) and a `q.coverage` event, and the UI says so under the answer.

Measured (`scripts/bench_big_files.py`, `results/phase1-big-files.md`, 4 vCPU): a 1,282 MB
PDF of 768 photo pages was read in 57 s with the reading process peaking at 175 MB, and a
320 MB file of the same kind at 167 MB: memory follows the window, not the file. Two bugs
were found on the way. The X-ray kept pdfium's whole document loaded (1,331 MB for this
file) until it reopened the document every 32 pages (96 MB). pdfminer's reference cycles
then grew the reading process to 730 MB until a garbage collection and `malloc_trim` ran
after each window. A first measurement also reported 4,150 MB for every row because
`ru_maxrss` survives `exec` on Linux; the script now reads `VmHWM`. Killed with SIGKILL
after 8 of 24 windows, the file resumed at window 8 with no window committed twice, and a
question asked from another process meanwhile searched the 256 pages read so far.

## 32. Hosted stores: Qdrant for vectors and keywords, S3 for files, a copied job store

`stores/qdrant.py` keeps each collection's vectors in a Qdrant collection with int8 scalar
quantization in RAM and the full vectors on disk; searches rescore the int8 shortlist with
the full vectors. On a real Qdrant 1.20 server with 3,000 random 384-dimension vectors, the
top 10 matched the exact scan in all 50 queries. Keywords are a second Qdrant collection of
sparse vectors with Qdrant's IDF modifier: BM25 with a fixed average length (Qdrant keeps
IDF statistics, not document lengths), updated in place instead of rebuilt per upload.
Dense and sparse live in separate collections so the two interfaces stay independent; the
app still fuses ranks and runs the cross-encoder itself, as decision 3 requires.

`stores/s3.py` speaks S3, which is what Cloudflare R2 is. Parsers need files on disk, so an
object is downloaded once into a cache folder; originals are named by content hash, so the
cache cannot go stale. An upload moved into the store also stays as the cached copy.

The job store copies its SQLite file to the blob store (an online backup, at most every 30
seconds and on close) and restores it on a fresh disk. Unfinished files do not depend on it:
they resume from their own checkpoints in the blob store.

Tests run the same code against Qdrant's in-process mode and moto's S3 server, including a
"wiped disk" case: a second store with an empty local folder finds the collection, answers
the same question with the same passages, and renders a cited page.

The plan's direct-to-R2 browser upload (A1 option 1) was not built: parts go through the
API (decision 31), which works on any host, and the API stages each finished file into R2.
Its cost is that upload bytes cross the app server once.

## 33. Page and embedding caches

A PDF page's parsed text is cached in the blob store under its X-ray content hash (text
without running lines, plus its images' raw bytes), route, OCR engine, a fingerprint of the
running lines removed, and a parser version. Passages are embedded once per text and model
(a local SQLite file; losing it costs time only). In the test, version 2 of a 40-page
manual with one rewritten page parsed exactly that page; a resumed job never parses a page
twice either. The hash ignores page numbers in headers and footers, so pages that moved
because an earlier page was inserted are still recognised as unchanged.

## 34. The visualizer reads only the event log, and is checked against it

Plan v2 phase 3, built as the user chose (decision answers, question 3): the Metro strip
above the chat, a waterfall under each answer with a replay button, Rank Race and the
page's source as inspector tabs, and the Page Grid in the Files tab. The Galaxy is not part
of it (phase 4, side branch).

All of it is drawn by pure functions over the event list (`web/src/events.ts`, unit
tested): stages and their times, each station's state, and for the Rank Race the rank of
every fused passage at each stage of the last retrieval round and what the grader did with
it. A replay fetches the saved run and feeds the same functions, compressed to at most
three seconds, so a replay cannot draw anything the answer did not do. Passages are labelled
from the collection's file list (file name and page), since events carry ids only.

The acceptance checks are in the end-to-end script and CI: the strip's per-station
milliseconds and every waterfall row equal the saved run's events, the Rank Race has one row
per fused passage and marks exactly the passages the grader kept, a replay ends on the
same numbers, event-to-screen latency (stream message to painted frame) stayed under
100 ms (12 ms at most in the run here), and with `prefers-reduced-motion` the strip's
transitions and pulse are off. No chart library was added: the bump chart is a small SVG
and the bars are CSS, which kept the bundle at about 90 KB gzipped.

Pack answers (POST /ask) are not streamed and carry no events, so packs show the classic
step list and no strip.

## 35. Book structure: outline paths, summaries for questions about a whole, reading on demand

Plan v2 phase 5 (`structure.py`). Pages get their outline path (the PDF's bookmarks, read
with pypdfium2 5's `get_title`/`get_dest`; the earlier attribute calls failed silently and
returned no outline at all) in the titles of their passages. Files of 20 pages or more get
section summaries when they are read: extractive, chosen with the local embedder, no LLM.
A question about a whole ("what is chapter 3 about", "summarise the book", "compare
chapters 2 and 5") gets chapter summaries, one LLM call per chapter written from the
section summaries, then kept; they are searched first and a chapter named in the question
is put first.

The first measurement on the long-book set (`scripts/bench_book.py`) made things worse:
fact questions fell from 1.0 to 0.33 and the topic terms in the passages used for chapter
questions from 0.47 to 0.06. Two causes. Section summaries repeated sentences such as
"The reference code for page 23 is ...", which outranked the page that held the asked
fact; summaries are now left out of ordinary questions entirely (`PassagesOnly`, a filter
applied before fusion). And "the sentences nearest the centroid" are the most typical
ones, which in a book are its template lines; sentence shapes found in more than 30% of
sections are now skipped and the rest picked with maximal marginal relevance. With both
fixes the offline run is level with "before" (fact 1.0 both; topic terms in the kept
passages 0.825 both) at half a model call more per question; the offline stand-in cannot
write a summary answer, so the live run (`results/phase5-book-live.md`) is the comparison
that counts. Short documents get no summaries: on the 3-page test PDF a summary outranked
the page itself.

Live, with Groq's models answering (`results/phase5-book-live.md`, one run): fact questions
1.0 before and after; topic terms in the answers to the eight whole-book questions 0.34
before, 0.54 after; model calls per question 3.2 before, 3.5 after (the chapter summaries
included). The gain is uneven: "compare chapters 2 and 3" went from 0 to 0.63 and the
overall question from 0 to 0.2, while two single-chapter questions scored lower than
before (chapter 7: 1.0 to 0.5). One run per configuration, so single questions are noise;
the direction is the result.

Reading on demand (A5): the X-ray keeps each page's text layer, searchable with BM25 the
moment a file is uploaded. While files are being read, a question's best pages move their
windows to the front of the queue and the question waits up to 15 seconds for them
(`jit_wait_seconds`); the run log records which pages were promoted. In the test a question
about page 60 of 64 had its window read before the windows in between. Scanned pages have
no text layer, so they cannot be found this way and are read in order.

## 36. The Galaxy, on a side branch

Plan v2 phase 4, kept on `feat/galaxy` as decided (a demo and recording mode, not part of
the product). An Explore tab draws every passage of a collection as a point in 3D: PCA in
numpy, fitted once per state of the collection (`projection.py`, `GET /collections/{c}/map`),
with each question placed by the same projection (a `q.position` event). The latest
question's dense hits are blue, BM25 hits amber, passages both found white, the rest
dimmed, and lines join the question to the reranker's top 5, which are listed with their
real rerank, cosine and BM25 scores, because a projection's distances are a sketch (on the
20,000-passage test the three axes kept 6% of the variance). UMAP was left out (it needs
numba). three.js and @react-three/fiber are loaded only when the tab opens, so the rest of
the app stays at about 90 KB gzipped.

The metrics board under it adds up the last 20 saved runs: mean time per stage, model calls
and tokens per answer, the share of passages never retrieved, requests left with the
provider, and a histogram of the top rerank score (the out-of-scope signal).

Measured (`web/e2e/galaxy.mjs`): 20,000 passages drawn, the listed top 5 equal the saved
run's rerank hits, the question placed from its logged position. The frame rate was 27 fps,
below the plan's 50, but on SwiftShader, a software renderer on the CPU, because this
machine has no GPU; the target is for an integrated GPU and is not verified here.


## 37. The Galaxy shipped in main, behind a demo-mode setting

Decision 36 kept the Galaxy on a side branch. It was merged into `main` along with the rest
of the work, so the plan's intent ("a demo and recording mode, not part of the product") is
kept by a setting instead: `demo_mode` (`HYPER_RAG_DEMO_MODE=1`) is off by default, and the
Explore tab, with the Galaxy and the metrics board, is hidden unless it is on. The three.js
code was already loaded only when that tab opens, so a default install never downloads it.
Alternatives were a normal tab for everyone (more screen for a view that is a sketch of the
data) and removing it from `main` (the work is in git history, but a demo you cannot switch
on is a demo nobody records). The cost: the metrics board is hidden with it, though it is
product-useful; if it is wanted day to day, it should move to its own tab.

## 38. Host readiness: warm-up, a quota guard, a settings check

Phase 6 adds three things for a free host, none of which touch retrieval or answers.
**Warm-up:** the embedding and reranking models load on a background thread at start-up, so
`GET /health` answers at once with `warm: warming | ready | failed` (it is open without a
login and says nothing about data). The page shows a waking-up screen while `/health`
cannot be reached (a sleeping host) and a banner while the models load. A failed warm-up
does not stop the app: the models load on the first question instead. **Quota guard:**
questions, claim checks and LLM exports count toward `model_requests_per_hour` (default
120) per client address; over it the API answers 429 with Retry-After. It is a sliding
window kept in memory, so a restart forgets it, and behind a proxy the address is the
forwarded one only because uvicorn runs with `--proxy-headers`. The point is to stop one
runaway tab from spending Groq's 200K tokens a day, not to bill anyone. **Settings check:**
`hyper-rag doctor` and the start-up log report a missing key for the chosen provider, a
half-configured S3 or Qdrant, a local blob store on a host that wipes its disk, and a
missing password. On a host (a Space sets `SPACE_ID`) the missing password is an error.
`GET /ready` probes the stores behind the login and returns 503 with the failing probe.

## 39. The claim checker fails closed, and says what "not found" means

Deck card D4. A text is split into claims by one model call (at most 10; the model is asked
for 11 so that a longer text is reported as cut, because a model told "at most 10" never
shows that an 11th existed). Each claim is searched with the same hybrid retrieval the chat
uses, which is local and free, and the model judges four claims per call against three
passages each: `supported`, `contradicted` or `not_found`. A verdict only counts if it names
a passage that exists. A missing verdict, an unknown word or a made-up passage number all
become `not_found`, which the page words as "the documents do not settle this", never as
"false". Four claims per call keeps one call near 3,000 tokens, under Groq's 8,000 a minute.
Every verdict shows its passage and opens it in the source panel, because the model's
reading is the weakest link and the reader must be able to overrule it.
Not measured yet: how often a real model's verdicts agree with a person's. The tests cover
the plumbing against the rule-based stand-in, which judges by word overlap and a missing
figure, so they say nothing about verdict quality on a real model.

## 40. Export is built from the saved run, and Notion means Markdown

Deck card D6. `POST /collections/{c}/export` takes a run id, not text: the answer is read
from what the server saved when it answered, so an export can only contain what the system
said. Markdown (question, answer, sources with a flat quote each) needs no model and is the
Notion route: Notion, Obsidian and most editors convert pasted Markdown, and a Notion API
integration would need a token and a database id for a gain of one paste. The LinkedIn
outline costs one request and is the only format that calls a model; it is told to use only
the answer's facts, and the page says it is a draft that is not checked again. Refusals
export as refusals, and cannot be turned into a post. Not built: a LinkedIn variant that
runs the claim checker over its own draft before showing it.

## 41. The MCP server: five tools, local or remote, a pinned SDK

Deck card D1. `hyper-rag mcp` serves `list_collections`, `search`, `ask`, `get_source` and
`check_claims` over stdio, on local collections by default, or on a deployed app with
`--remote URL`, logging in with the password from `HYPER_RAG_REMOTE_PASSWORD` (an
environment variable, so it is not in shell history or a process list). `search` calls no
model, so it is the cheap way for another tool to look. All tools are read-only; `ask` and
`check_claims` spend model requests, and on a host count toward its hourly limit. Errors the
engine expects (no such collection, a rate limit, a wrong password) reach the calling model
as messages. The SDK is pinned to `mcp==1.30.0`: its 2.x line exists, and its API was not
checked here. Return types are `dict[str, Any]` because a bare `dict` makes the SDK send
text only. Verified through a real stdio client (list tools, ask, an error flagged as an
error), and in tests against both backends.

## 42. The metrics board gets its own tab

Decision 37 hid the metrics board with the Galaxy under demo mode, and called that a cost. It
now has a Metrics tab of its own, shown for every collection: time per stage, model calls and
tokens per answer, requests left with the provider, the never-retrieved share and the top
rerank score histogram, from the last 20 saved runs. Explore keeps only the Galaxy and stays
behind `demo_mode`. The board is plain DOM, so it adds nothing to what a default page loads.

## 43. A real-model quality check, and what it found

`scripts/quality_check.py` (results in `results/quality-check.md`) runs on Groq against the
eight fixture files. **Claims:** 30 hand-labelled claims (10 per verdict) go straight to
`judge_claims`, which was split out of `check_claims` so the split step cannot change what is
measured. All 30 were judged right, with none of the 20 unsupported claims called supported.
The set is easy by construction (one sentence each, one changed figure or name), so this is
a ceiling, and the labels are the author's. **Outlines:** 8 answers exported; none added a
figure that was not in its answer, but 4 of 8 added unsupported filler ("reduces downtime",
"becomes cash-flow positive"). The checker also missed true points that had lost their
subject ("Warranty length: 10 years"). Both findings argue for the outline self-check
(run the checker on an outline before showing it, after rewriting each point to stand
alone); it was not built in this round.
