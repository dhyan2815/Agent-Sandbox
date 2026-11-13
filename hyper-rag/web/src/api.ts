// The server's API: types for what it returns, fetch helpers, and the answer stream reader.

export interface Config {
  offline: boolean;
  generator: string;
  ocr: string;
  max_upload_mb: number;
  extensions: string[];
  login: boolean;
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

export interface FileRecord {
  id: string;
  name: string;
  suffix: string;
  kind: string;
  size: number;
  chunks: number;
  seconds: number;
  report: FileReport;
  duplicate?: boolean;
  replaced?: boolean;
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
