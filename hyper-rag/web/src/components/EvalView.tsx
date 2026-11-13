import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { type Config, type EvalStatus, type MetricRow, api, postJson } from "../api";

const RETRIEVAL_COLUMNS: [string, string][] = [
  ["mode", "Search mode"],
  ["recall@5", "Right page in top 5"],
  ["mrr", "MRR"],
  ["ndcg@10", "nDCG@10"],
  ["facts@5", "Fact in top 5"],
];
const ANSWER_COLUMNS: [string, string][] = [
  ["config", "Configuration"],
  ["key_facts", "Contains the fact"],
  ["citation_precision", "Cites the right page"],
  ["correctness", "Correct (judged)"],
  ["grounded", "Grounded (judged)"],
  ["refused_answerable", "Wrongly declined"],
  ["llm_calls", "Model calls"],
];
const LABELS: Record<string, string> = {
  vector: "Vector only",
  hybrid: "Vector + keyword",
  hybrid_rerank: "Hybrid + rerank",
  agent: "Full agent",
};

function MetricTable({ rows, columns }: { rows: MetricRow[]; columns: [string, string][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map(([key, label], i) => (
              <th key={key} className={i ? "num" : ""}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {columns.map(([key], i) => (
                <td key={key} className={i ? "num" : ""}>
                  {i ? String(row[key]) : (LABELS[String(row[key])] ?? String(row[key]))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EvalView({ slug, config }: { slug: string; config: Config }) {
  const client = useQueryClient();
  const [questions, setQuestions] = useState(8);
  const [agent, setAgent] = useState(true);
  const [judge, setJudge] = useState(false);
  const [regenerate, setRegenerate] = useState(false);

  const status = useQuery({
    queryKey: ["eval", slug],
    queryFn: () => api<EvalStatus>(`/collections/${slug}/eval`),
    // Poll while a run is going; stop as soon as it is done or failed.
    refetchInterval: (query) => (query.state.data?.state === "running" ? 1500 : false),
  });

  const run = async () => {
    try {
      await postJson(`/collections/${slug}/eval`, { questions, agent, judge, regenerate });
      setRegenerate(false);
    } catch (error) {
      alert((error as Error).message);
    }
    client.invalidateQueries({ queryKey: ["eval", slug] });
  };

  const perQuestion = 2 + (agent ? 4 : 0) + (judge ? 2 * (1 + (agent ? 1 : 0)) : 0);
  const data = status.data;
  const running = data?.state === "running";
  const log = [...(data?.log ?? []), data?.error ? `Stopped: ${data.error}` : ""].filter(Boolean);
  const report = data?.report;

  return (
    <div className="view" id="eval-view">
      <div className="pad">
        <h3 className="section" style={{ marginTop: 0 }}>
          How well does it work on these documents?
        </h3>
        <p className="note">
          This writes test questions from passages of your own documents, then measures whether
          retrieval finds the right page and whether the answers contain the expected fact and
          cite the right source. The questions are written from the passages they are scored
          against, so they are easier than real ones: treat the result as a health check, not a
          benchmark.
        </p>
        <div className="controls">
          <label>
            Questions{" "}
            <input
              id="eval-n"
              type="number"
              min={2}
              max={30}
              value={questions}
              onChange={(e) => setQuestions(Number(e.target.value) || 8)}
            />
          </label>
          <label>
            <input id="eval-agent" type="checkbox" checked={agent} onChange={(e) => setAgent(e.target.checked)} />{" "}
            Also test the full agent
          </label>
          <label>
            <input id="eval-judge" type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} />{" "}
            Judge correctness with a second model
          </label>
          <label>
            <input id="eval-new" type="checkbox" checked={regenerate} onChange={(e) => setRegenerate(e.target.checked)} />{" "}
            Write new questions
          </label>
          <button className="primary" id="eval-run" disabled={running} onClick={run}>
            {running ? "Running…" : "Run evaluation"}
          </button>
        </div>
        {!config.offline && (
          <p className="note" id="eval-cost">
            About {questions * perQuestion} model calls with these settings. On a free tier that
            can take several minutes; finished work is saved and a re-run continues from it.
          </p>
        )}
        {(log.length > 0 || status.error) && (
          <pre className="log" id="eval-log">
            {status.error ? (status.error as Error).message : log.join("\n")}
          </pre>
        )}
        {report && (
          <div id="eval-report">
            <h3 className="section">Search: does it find the right page?</h3>
            <p className="note">
              {report.questions} generated questions over {report.chunks} passages. Run on {report.date}.
            </p>
            <MetricTable rows={report.retrieval} columns={RETRIEVAL_COLUMNS} />
            <h3 className="section">Answers</h3>
            <p className="note">
              Answers by {report.generator}; judge: {report.judge}. "n/a" means that metric was not run.
            </p>
            <MetricTable rows={report.answers} columns={ANSWER_COLUMNS} />
            <h3 className="section">The questions it was tested on</h3>
            <ol className="golden">
              {report.golden.map((g, i) => (
                <li key={i}>
                  {g.question}
                  <small>
                    Expected: {g.reference_answer} (from {g.source_title})
                  </small>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
