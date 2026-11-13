import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { type EngineEvent, type Hit, quota, stages, totals } from "../events";

interface RunSummary {
  id: string;
}

interface Run {
  id: string;
  events: EngineEvent[];
}

const RECENT = 20;

/** The metrics board: the last answers' saved runs, added up. */
export function Metrics({ slug, passages }: { slug: string; passages: number }) {
  const runs = useQuery({
    queryKey: ["runs", slug],
    queryFn: async () => {
      const list = (await api<{ runs: RunSummary[] }>(`/collections/${slug}/runs`)).runs.slice(0, RECENT);
      return Promise.all(list.map((r) => api<Run>(`/collections/${slug}/runs/${r.id}`)));
    },
  });
  const all = runs.data ?? [];
  if (!all.length) return <p className="note">No answers yet: the board fills in as questions are asked.</p>;

  const byStage = new Map<string, number[]>();
  for (const run of all)
    for (const stage of stages(run.events)) byStage.set(stage.label, [...(byStage.get(stage.label) ?? []), stage.ms]);
  const mean = (values: number[]) => values.reduce((a, b) => a + b, 0) / values.length;
  const stageRows = [...byStage.entries()].map(([label, values]) => [label, mean(values)] as const);
  const longest = Math.max(...stageRows.map(([, ms]) => ms), 1);
  const sums = all.map((run) => totals(run.events));
  const tops = all
    .map((run) => run.events.filter((e) => e.t === "r.rerank").at(-1)?.top_score)
    .filter((s): s is number => typeof s === "number");
  const seen = new Set<string>();
  for (const run of all)
    for (const event of run.events)
      if (["r.dense", "r.bm25", "r.rerank"].includes(event.t))
        for (const hit of (event.hits as Hit[]) ?? []) seen.add(hit.id);
  const budget = quota(all.flatMap((r) => r.events));
  const lo = Math.min(...tops, 0);
  const hi = Math.max(...tops, 1);
  const bins = new Array(8).fill(0);
  for (const score of tops) bins[Math.min(7, Math.floor(((score - lo) / (hi - lo || 1)) * 8))] += 1;
  const tallest = Math.max(...bins, 1);

  return (
    <div className="metrics" data-testid="metrics">
      <section>
        <h4>Time per stage (mean of the last {all.length} answers)</h4>
        {stageRows.map(([label, ms]) => (
          <div key={label} className="metric-bar">
            <span>{label}</span>
            <span className="track"><span style={{ width: `${(100 * ms) / longest}%` }} /></span>
            <span className="num">{ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms.toFixed(ms < 10 ? 1 : 0)} ms`}</span>
          </div>
        ))}
      </section>
      <section className="tiles">
        <div><strong>{mean(sums.map((s) => s.calls)).toFixed(1)}</strong><span>model calls per answer</span></div>
        <div><strong>{Math.round(mean(sums.map((s) => s.tokens))).toLocaleString()}</strong><span>tokens per answer</span></div>
        <div>
          <strong>{passages ? `${((100 * (passages - Math.min(seen.size, passages))) / passages).toFixed(1)}%` : "–"}</strong>
          <span>of passages never retrieved</span>
        </div>
        <div>
          <strong>{typeof budget?.requests_left_today === "number" ? budget.requests_left_today.toLocaleString() : "–"}</strong>
          <span>model requests left today</span>
        </div>
      </section>
      <section>
        <h4>Top rerank score per answer</h4>
        <div className="histogram" role="img" aria-label="Histogram of the top rerank score">
          {bins.map((count, i) => (
            <span key={i} title={`${count} answers`} style={{ height: `${(100 * count) / tallest}%` }} />
          ))}
        </div>
        <p className="note">
          From {lo.toFixed(2)} to {hi.toFixed(2)}. A low top score is the out-of-scope signal on the README's to-do
          list: nothing the reranker saw was a good match.
        </p>
      </section>
    </div>
  );
}
