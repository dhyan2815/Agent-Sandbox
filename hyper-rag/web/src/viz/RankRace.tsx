import { RACE_COLUMNS, type EngineEvent, type Runner, rankRace } from "../events";

const COLUMN_LABELS: Record<string, string> = {
  dense: "Dense",
  bm25: "BM25",
  fuse: "RRF",
  rerank: "Rerank",
  fate: "Grader",
};

interface Props {
  events: EngineEvent[];
  label: (chunkId: string) => string;
  onOpen?: (chunkId: string) => void;
}

/**
 * Rank Race: one line per passage that reached fusion, across Dense, BM25, RRF, Rerank and
 * the grader. It answers "why was this passage cited and that one not?". Positions are the
 * real ranks from the events; a passage a stage did not return sits below the last row.
 */
export function RankRace({ events, label, onOpen }: Props) {
  const runners = rankRace(events);
  if (!runners.length) return <p className="note">No retrieval in this answer.</p>;
  const rows = Math.max(...runners.map((r) => Math.max(r.dense ?? 0, r.bm25 ?? 0, r.fuse ?? 0)), runners.length);
  const height = 22;
  const width = 300;
  const columns = [...RACE_COLUMNS, "fate"] as const;
  const x = (i: number) => 30 + (i * (width - 60)) / (columns.length - 1);
  const missing = rows + 1;
  const y = (rank: number | null) => 18 + ((rank ?? missing) - 1) * height;
  const fateRank = (runner: Runner) =>
    runner.fate === "kept" ? runner.rerank : runner.fate === "dropped" ? runner.rerank : null;
  const sorted = [...runners].sort((a, b) => (a.fuse ?? 99) - (b.fuse ?? 99));

  return (
    <div className="race" data-testid="rank-race">
      <svg viewBox={`0 0 ${width} ${y(missing) + 16}`} role="img" aria-label="How each passage's rank changed at each stage">
        {columns.map((column, i) => (
          <text key={column} x={x(i)} y={10} className="col">
            {COLUMN_LABELS[column]}
          </text>
        ))}
        <text x={4} y={y(missing) + 4} className="missing">not returned</text>
        {sorted.map((runner) => {
          const ranks = [runner.dense, runner.bm25, runner.fuse, runner.rerank, fateRank(runner)];
          const points = ranks.map((rank, i) => `${x(i)},${y(rank)}`).join(" ");
          return (
            <g key={runner.id} className={`runner ${runner.fate}`} data-runner={runner.id}>
              <polyline points={points} />
              {ranks.map((rank, i) => (
                <circle key={i} cx={x(i)} cy={y(rank)} r={rank === null ? 2 : 4}>
                  <title>
                    {label(runner.id)}: {COLUMN_LABELS[columns[i]]} {rank === null ? "not returned" : `rank ${rank}`}
                  </title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <table className="race-table">
        <thead>
          <tr>
            <th>Passage</th>
            <th className="num">Dense</th>
            <th className="num">BM25</th>
            <th className="num">RRF</th>
            <th className="num">Rerank</th>
            <th>Grader</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((runner) => (
            <tr key={runner.id} className={runner.fate} data-runner={runner.id}>
              <td className="name">
                {onOpen ? (
                  <button type="button" className="link" onClick={() => onOpen(runner.id)}>
                    {label(runner.id)}
                  </button>
                ) : (
                  label(runner.id)
                )}
              </td>
              <td className="num">{runner.dense ?? "–"}</td>
              <td className="num">{runner.bm25 ?? "–"}</td>
              <td className="num">{runner.fuse ?? "–"}</td>
              <td className="num">
                {runner.rerank ?? "–"}
                {runner.rerankScore !== null ? ` (${runner.rerankScore.toFixed(2)})` : ""}
              </td>
              <td>{runner.fate === "cut" ? "not shown" : runner.fate}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">
        Ranks come from this answer's saved events. Scores differ between stages (cosine, BM25,
        fusion points, cross-encoder), so only the ranks are compared across columns.
      </p>
    </div>
  );
}
