import { describe, expect, it } from "vitest";
import { type EngineEvent, metro, rankRace, stages, totals } from "./events";

const hit = (id: string, rank: number, score = 1 / rank) => ({ id, rank, score });

// A real-shaped run: one rewrite, then an answer.
const RUN: EngineEvent[] = [
  { t: "a.retrieve", query: "q", attempt: 1 },
  { t: "q.embed", ms: 9 },
  { t: "r.dense", hits: [hit("a", 1), hit("b", 2)], ms: 1 },
  { t: "r.bm25", hits: [hit("c", 1)], ms: 2 },
  { t: "r.fuse", hits: [hit("a", 1), hit("c", 2), hit("b", 3)], ms: 0.1 },
  { t: "r.rerank", hits: [hit("c", 1, 7.9), hit("a", 2, 1.2)], top_score: 7.9, ms: 120 },
  { t: "a.grade", kept: [], dropped: ["c", "a"], ms: 650, model: "m", tokens_in: 1000, tokens_out: 20 },
  { t: "a.rewrite", query: "q2", attempt: 1, ms: 300, model: "m" },
  { t: "a.retrieve", query: "q2", attempt: 2 },
  { t: "q.embed", ms: 8 },
  { t: "r.dense", hits: [hit("d", 1), hit("a", 2)], ms: 1 },
  { t: "r.bm25", hits: [hit("a", 1), hit("e", 2)], ms: 2 },
  { t: "r.fuse", hits: [hit("a", 1), hit("d", 2), hit("e", 3)], ms: 0.1 },
  { t: "r.rerank", hits: [hit("a", 1, 5), hit("e", 2, 3)], top_score: 5, ms: 100 },
  { t: "a.grade", kept: ["a"], dropped: ["e"], ms: 600, model: "m" },
  { t: "a.generate", insufficient: false, ms: 2100, model: "m", tokens_in: 2900, tokens_out: 120 },
  { t: "a.check", grounded: true, ms: 700, model: "m", cached: true },
  { t: "llm.quota", model: "m", requests_left_today: 990 },
];

describe("stages and totals", () => {
  it("lists every timed step in order, with what it decided", () => {
    const all = stages(RUN);
    expect(all.map((s) => s.label)).toEqual([
      "Embed", "Dense", "BM25", "RRF", "Rerank", "Grade", "Rewrite",
      "Embed", "Dense", "BM25", "RRF", "Rerank", "Grade", "Write", "Check",
    ]);
    expect(all[5].detail).toBe("0 of 2 kept");
    expect(all[14]).toMatchObject({ detail: "grounded", cached: true });
    expect(totals(RUN)).toEqual({ ms: 4593, calls: 5, tokens: 4040 });
  });
});

describe("metro", () => {
  it("adds up repeated stations and shows the last round's counts", () => {
    const stations = Object.fromEntries(metro(RUN, true).map((s) => [s.key, s]));
    expect(stations.embed).toMatchObject({ state: "done", ms: 17 });
    expect(stations.search.value).toBe("2 / 2");
    expect(stations.grade.value).toBe("1/2");
    expect(stations.rewrite).toMatchObject({ state: "done", value: "×1" });
    expect(stations.condense.state).toBe("skipped");
    expect(stations.check.value).toBe("✓");
  });

  it("lights the station the engine is working on", () => {
    const states = (events: EngineEvent[]) =>
      metro(events, false).filter((s) => s.state === "active").map((s) => s.key);
    expect(states([])).toEqual(["embed"]);
    expect(states(RUN.slice(0, 6))).toEqual(["grade"]);
    expect(states(RUN.slice(0, 7))).toEqual(["rewrite"]);
    expect(states(RUN.slice(0, 16))).toEqual(["check"]);
  });
});

describe("rankRace", () => {
  it("follows the last round's passages through every stage to their fate", () => {
    const race = Object.fromEntries(rankRace(RUN).map((r) => [r.id, r]));
    expect(Object.keys(race)).toEqual(["a", "d", "e"]);
    expect(race.a).toMatchObject({ dense: 2, bm25: 1, fuse: 1, rerank: 1, fate: "kept" });
    expect(race.e).toMatchObject({ dense: null, bm25: 2, rerank: 2, fate: "dropped" });
    expect(race.d).toMatchObject({ rerank: null, fate: "cut" });
  });
});
