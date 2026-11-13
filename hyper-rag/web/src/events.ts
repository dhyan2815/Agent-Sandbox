// Engine events (hyper_rag/events.py) turned into what the visualizer draws.
//
// Every function here is pure and works from the event log alone, which is what makes the
// rule of the visualizer checkable: every number on screen comes from a real event, and a
// replay of a saved run draws exactly what the live answer drew.

export type EngineEvent = { t: string } & Record<string, unknown>;

export interface Hit {
  id: string;
  rank: number;
  score: number;
}

const num = (value: unknown) => (typeof value === "number" ? value : 0);
const hits = (event: EngineEvent | undefined): Hit[] =>
  (event?.hits as Hit[] | undefined) ?? [];

// --- stages: one per step that took time, in the order they happened --------------------

export interface Stage {
  key: string; // the station it belongs to
  label: string;
  ms: number;
  detail: string;
  tokens: number; // tokens in + out, when the provider reported them
  cached: boolean;
}

const LLM_STAGES: Record<string, [string, string]> = {
  "q.condense": ["condense", "Condense"],
  "a.route": ["route", "Route"],
  "a.grade": ["grade", "Grade"],
  "a.rewrite": ["rewrite", "Rewrite"],
  "a.generate": ["generate", "Write"],
  "a.check": ["check", "Check"],
  "a.summarize": ["summarize", "Summarise"],
};

const RETRIEVAL_STAGES: Record<string, [string, string]> = {
  "q.embed": ["embed", "Embed"],
  "r.dense": ["search", "Dense"],
  "r.bm25": ["search", "BM25"],
  "r.fuse": ["fuse", "RRF"],
  "r.rerank": ["rerank", "Rerank"],
};

export function stages(events: EngineEvent[]): Stage[] {
  const out: Stage[] = [];
  for (const event of events) {
    const llm = LLM_STAGES[event.t];
    const retrieval = RETRIEVAL_STAGES[event.t];
    if (!llm && !retrieval) continue;
    const [key, label] = llm ?? retrieval;
    let detail = "";
    if (event.t === "a.grade") {
      const kept = (event.kept as string[]).length;
      detail = `${kept} of ${kept + (event.dropped as string[]).length} kept`;
    } else if (event.t === "a.check") detail = event.grounded ? "grounded" : "not grounded";
    else if (event.t === "a.route") detail = String(event.route);
    else if (event.t === "a.rewrite") detail = `“${event.query}”`;
    else if (event.t === "a.generate") detail = event.insufficient ? "no answer in passages" : "";
    else if (event.t === "q.condense") detail = `“${event.standalone}”`;
    else if (event.t === "a.summarize") detail = `chapter ${event.chapter}: ${event.title}`;
    else if (retrieval && event.t !== "q.embed") detail = `${hits(event).length} passages`;
    out.push({
      key,
      label,
      ms: num(event.ms),
      detail,
      tokens: num(event.tokens_in) + num(event.tokens_out),
      cached: event.cached === true,
    });
  }
  return out;
}

export interface Totals {
  ms: number;
  calls: number;
  tokens: number;
}

export function totals(events: EngineEvent[]): Totals {
  const all = stages(events);
  return {
    ms: Math.round(all.reduce((sum, s) => sum + s.ms, 0)),
    calls: events.filter((e) => e.t in LLM_STAGES).length,
    tokens: all.reduce((sum, s) => sum + s.tokens, 0),
  };
}

// --- the metro strip: one station per pipeline step, with its latest state -------------

export type StationState = "idle" | "active" | "done" | "skipped";

export interface Station {
  key: string;
  label: string;
  state: StationState;
  value: string; // the short number under the station
  ms: number;
}

export const STATIONS: [string, string][] = [
  ["condense", "Condense"],
  ["embed", "Embed"],
  ["search", "Dense/BM25"],
  ["fuse", "RRF"],
  ["rerank", "Rerank"],
  ["grade", "Grade"],
  ["rewrite", "Rewrite"],
  ["generate", "Write"],
  ["check", "Check"],
];

// What the engine does after each event, so the next station can light up as "working".
const NEXT: Record<string, string> = {
  "a.retrieve": "embed",
  "q.embed": "search",
  "r.bm25": "fuse",
  "r.fuse": "rerank",
  "r.rerank": "grade",
  "a.rewrite": "embed",
  "q.condense": "embed",
};

export function metro(events: EngineEvent[], finished: boolean): Station[] {
  const done = new Map<string, Station>();
  for (const stage of stages(events)) {
    const before = done.get(stage.key);
    done.set(stage.key, {
      key: stage.key,
      label: "",
      state: "done",
      ms: (before?.ms ?? 0) + stage.ms,
      value: "",
    });
  }
  const dense = hits(lastOf(events, "r.dense")).length;
  const bm25 = hits(lastOf(events, "r.bm25")).length;
  const fuse = hits(lastOf(events, "r.fuse")).length;
  const rerank = hits(lastOf(events, "r.rerank")).length;
  const grade = lastOf(events, "a.grade");
  const check = lastOf(events, "a.check");
  const rewrites = events.filter((e) => e.t === "a.rewrite").length;
  const values: Record<string, string> = {
    search: dense || bm25 ? `${dense} / ${bm25}` : "",
    fuse: fuse ? String(fuse) : "",
    rerank: rerank ? String(rerank) : "",
    grade: grade
      ? `${(grade.kept as string[]).length}/${(grade.kept as string[]).length + (grade.dropped as string[]).length}`
      : "",
    rewrite: rewrites ? `×${rewrites}` : "",
    check: check ? (check.grounded ? "✓" : "✗") : "",
  };
  const last = events[events.length - 1];
  let active = !finished && last ? NEXT[last.t] : undefined;
  if (!finished && last && !active) {
    if (last.t === "a.grade") active = (last.kept as string[]).length ? "generate" : "rewrite";
    if (last.t === "a.generate") active = "check";
  }
  if (!finished && !last) active = "embed";
  return STATIONS.map(([key, label]) => {
    const seen = done.get(key);
    let state: StationState = seen ? "done" : "idle";
    if (key === active) state = "active";
    if (finished && !seen) state = "skipped";
    return { key, label, state, ms: Math.round(seen?.ms ?? 0), value: values[key] ?? "" };
  });
}

function lastOf(events: EngineEvent[], name: string): EngineEvent | undefined {
  for (let i = events.length - 1; i >= 0; i--) if (events[i].t === name) return events[i];
  return undefined;
}

// --- the rank race: where each candidate stood at each stage ----------------------------

export type Fate = "kept" | "dropped" | "cut";

export interface Runner {
  id: string;
  dense: number | null;
  bm25: number | null;
  fuse: number | null;
  rerank: number | null;
  fate: Fate; // kept by the grader, dropped by it, or cut before it saw the passage
  rerankScore: number | null;
}

export const RACE_COLUMNS = ["dense", "bm25", "fuse", "rerank"] as const;

/** The last retrieval round (after any rewrites), as one line per passage the fusion kept. */
export function rankRace(events: EngineEvent[]): Runner[] {
  let start = 0;
  events.forEach((e, i) => {
    if (e.t === "a.retrieve") start = i;
  });
  const round = events.slice(start);
  const rankOf = (name: string) =>
    new Map(hits(round.find((e) => e.t === name)).map((h) => [h.id, h]));
  const dense = rankOf("r.dense");
  const bm25 = rankOf("r.bm25");
  const fuse = rankOf("r.fuse");
  const rerank = rankOf("r.rerank");
  const grade = round.find((e) => e.t === "a.grade");
  const kept = new Set((grade?.kept as string[] | undefined) ?? []);
  const ids = [...fuse.keys()].length ? [...fuse.keys()] : [...dense.keys()];
  return ids.map((id) => ({
    id,
    dense: dense.get(id)?.rank ?? null,
    bm25: bm25.get(id)?.rank ?? null,
    fuse: fuse.get(id)?.rank ?? null,
    rerank: rerank.get(id)?.rank ?? null,
    rerankScore: rerank.get(id)?.score ?? null,
    fate: kept.has(id) ? "kept" : rerank.has(id) ? "dropped" : "cut",
  }));
}

/** The latest provider budget seen in the events, if the provider reports one. */
export function quota(events: EngineEvent[]): EngineEvent | undefined {
  return lastOf(events, "llm.quota");
}
