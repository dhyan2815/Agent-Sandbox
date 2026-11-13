// The server's API: types for what it returns, fetch helpers, and the answer stream reader.

export interface Config {
  offline: boolean;
  generator: string;
  ocr: string;
  max_upload_mb: number;
  extensions: string[];
  login: boolean;
  demo_mode: boolean;
}

export interface FileReport {
  kind: string;
  units: number;
  unit_name: string;
  tables: number;
  images: number;
  images_with_text: number;
  ocr_units: number;
  characters: number;
  warnings: string[];
}

export interface XRaySummary {
  pages: number;
  routes: Record<string, number>;
  estimate_seconds: number;
  boilerplate_lines: number;
  outline_entries: number;
  warning?: string;
}

export interface FileRecord {
  id: string;
  name: string;
  suffix: string;
  kind: string;
  size: number;
  chunks: number;
  seconds?: number;
  report: FileReport | null;
  status?: "queued" | "reading" | "ready" | "failed";
  pages_total?: number | null;
  pages_done?: number;
  windows_total?: number | null;
  windows_done?: number;
  xray?: XRaySummary | null;
  error?: string | null;
  duplicate?: boolean;
  replaced?: boolean;
}

export interface Reading {
  file_id: string;
  name: string;
  status: string;
  pages_done: number;
  pages_total: number | null;
}

export interface Collection {
  slug: string;
  name: string;
  description: string;
  created: string;
  updated: string;
  files: FileRecord[];
}

export interface Citation {
  number: number;
  title: string;
  url: string;
  chunk_id: string;
  doc_id: string;
  text: string;
}

export interface AnswerBody {
  question: string;
  answer: string;
  refused: boolean;
  citations: Citation[];
  trace: string[];
  llm_calls: number;
  run_id?: string | null;
  reading?: Reading[];
}

export interface ClaimPassage {
  title: string;
  url: string;
  chunk_id: string;
  doc_id: string;
  text: string;
}

export type Verdict = "supported" | "contradicted" | "not_found";

export interface CheckedClaim {
  claim: string;
  verdict: Verdict;
  evidence: ClaimPassage | null;
  closest: ClaimPassage | null;
}

export interface ClaimReport {
  claims: CheckedClaim[];
  summary: Record<Verdict, number>;
  llm_calls: number;
  truncated: boolean;
}

export interface Span {
  text: string;
  hit: boolean;
}

export interface Source {
  file_id: string;
  file_name: string;
  kind: string;
  unit_name: string;
  unit_number: number;
  unit_label: string;
  read_by_ocr: boolean;
  file_url: string;
  preview_url: string | null;
  lines: Span[][];
}

export type MetricRow = Record<string, string | number>;

export interface EvalReport {
  questions: number;
  chunks: number;
  date: string;
  generator: string;
  judge: string;
  retrieval: MetricRow[];
  answers: MetricRow[];
  golden: { question: string; reference_answer: string; source_title: string }[];
}

export interface EvalStatus {
  state: "idle" | "running" | "done" | "failed";
  log: string[];
  report: EvalReport | null;
  error: string | null;
}

/** One message of the answer stream (POST /collections/{c}/ask/stream). */
export type StreamMessage =
  | { type: "step"; text: string }
  | ({ type: "event"; t: string } & Record<string, unknown>)
  | ({ type: "answer" } & AnswerBody)
  | { type: "error"; detail: string };

export class ApiError extends Error {}

// A login is required and the session has ended (or never started): go and log in.
function toLogin(response: Response): void {
  if (response.status === 401) window.location.assign("/login");
}

async function errorText(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  const detail = Array.isArray(body.detail)
    ? body.detail.map((d: { msg: string }) => d.msg).join("; ")
    : body.detail;
  return detail || `Request failed (${response.status})`;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, options);
  toLogin(response);
  if (!response.ok) throw new ApiError(await errorText(response));
  if (response.status === 204) return null as T;
  return (await response.json()) as T;
}

export const postJson = <T>(path: string, data: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

/**
 * Splits server-sent events out of a text stream that arrives in arbitrary pieces.
 * Feed it each decoded piece; it returns the complete "data: {...}" messages so far.
 */
export function sseReader(): (piece: string) => StreamMessage[] {
  let buffer = "";
  return (piece) => {
    buffer += piece;
    const messages: StreamMessage[] = [];
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      if (block.startsWith("data: ")) messages.push(JSON.parse(block.slice(6)));
    }
    return messages;
  };
}

/** POST and read the answer stream, calling onMessage for each message as it arrives. */
export async function streamAnswer(
  path: string,
  payload: unknown,
  onMessage: (message: StreamMessage) => void,
): Promise<void> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  toLogin(response);
  if (!response.ok || !response.body) throw new ApiError(await errorText(response));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const read = sseReader();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    for (const message of read(decoder.decode(value, { stream: true }))) onMessage(message);
  }
}

/** Files that are still being read: the collection list should keep refreshing. */
export const isReading = (file: FileRecord) => file.status === "queued" || file.status === "reading";

interface UploadSession {
  id: string;
  received: number;
  size: number;
  part_size: number;
}

/**
 * Send a file in parts (resumable upload). A failed part is retried after asking the
 * server how much it has, so a dropped connection resumes instead of starting over.
 */
export async function uploadResumable(
  slug: string,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<FileRecord> {
  const session = await postJson<UploadSession>(`/collections/${slug}/uploads`, {
    name: file.name,
    size: file.size,
  });
  const url = `/collections/${slug}/uploads/${session.id}`;
  let offset = session.received;
  let failures = 0;
  while (offset < file.size) {
    const part = file.slice(offset, offset + session.part_size);
    try {
      const response = await fetch(`${url}?offset=${offset}`, { method: "PUT", body: part });
      toLogin(response);
      if (response.status === 409) {
        offset = (await response.json()).received; // the server already has more (or less)
        continue;
      }
      if (!response.ok) throw new ApiError(await errorText(response));
      offset = (await response.json()).received;
      failures = 0;
      onProgress(offset / file.size);
    } catch (error) {
      if (error instanceof ApiError || ++failures > 5) throw error;
      await new Promise((resolve) => setTimeout(resolve, 1000 * failures));
      offset = (await api<UploadSession>(url)).received; // resume where the server is
    }
  }
  return api<FileRecord>(`${url}/complete`, { method: "POST" });
}
