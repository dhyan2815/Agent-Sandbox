import { useState } from "react";
import { type Citation, type ClaimPassage, type ClaimReport, type Verdict, postJson } from "../api";

export const VERDICT_LABEL: Record<Verdict, string> = {
  supported: "Supported",
  contradicted: "Contradicted",
  not_found: "Not found in your documents",
};

const MIN = 20;
const MAX = 4000;

/** Claim checker: paste a draft, see each claim judged against the collection's passages. */
export function CheckView({
  slug,
  onCite,
}: {
  slug: string;
  onCite: (citation: Citation) => void;
}) {
  const [text, setText] = useState("");
  const [report, setReport] = useState<ClaimReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const open = (passage: ClaimPassage) => onCite({ number: 0, ...passage });
  const run = async () => {
    setBusy(true);
    setError("");
    try {
      setReport(await postJson<ClaimReport>(`/collections/${slug}/check`, { text }));
    } catch (failure) {
      setReport(null);
      setError((failure as Error).message);
    }
    setBusy(false);
  };
  const ready = text.trim().length >= MIN && !busy;

  return (
    <div className="view" id="check-view">
      <div className="pad">
        <h3 className="section" style={{ marginTop: 0 }}>
          Check a text against these documents
        </h3>
        <p className="note">
          Paste a draft, a report or an answer from somewhere else. Each factual claim in it is
          looked up in your documents and marked supported, contradicted or not found. The passage
          is shown next to every verdict: read it before you rely on the verdict. "Not found" means
          the documents do not settle the claim, not that it is false.
        </p>
        <textarea
          id="check-text"
          className="check-text"
          rows={7}
          maxLength={MAX}
          placeholder="Paste the text to check"
          aria-label="Text to check"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <div className="controls">
          <button className="primary" id="check-run" disabled={!ready} onClick={run}>
            {busy ? "Checking…" : "Check claims"}
          </button>
          <span className="note">
            {text.length}/{MAX} characters. Uses a few model requests (one per four claims, plus one).
          </span>
        </div>
        {error && <p className="error">{error}</p>}
        {report && <CheckResult report={report} onOpen={open} />}
      </div>
    </div>
  );
}

function CheckResult({ report, onOpen }: { report: ClaimReport; onOpen: (p: ClaimPassage) => void }) {
  const { summary } = report;
  return (
    <div className="check-result" data-testid="check-result">
      <p className="check-summary">
        <strong>{report.claims.length}</strong> claims:{" "}
        <span className="v-supported">{summary.supported} supported</span>,{" "}
        <span className="v-contradicted">{summary.contradicted} contradicted</span>,{" "}
        <span className="v-not_found">{summary.not_found} not found</span>
      </p>
      {report.truncated && (
        <p className="note">The text has more claims than were checked. Only the first were.</p>
      )}
      <ol className="claims">
        {report.claims.map((claim, i) => {
          const passage = claim.evidence ?? claim.closest;
          return (
            <li key={i} className={`claim v-${claim.verdict}`} data-verdict={claim.verdict}>
              <div className="claim-head">
                <span className={`verdict v-${claim.verdict}`}>{VERDICT_LABEL[claim.verdict]}</span>
                <span className="claim-text">{claim.claim}</span>
              </div>
              {passage && (
                <button className="claim-passage" onClick={() => onOpen(passage)}>
                  <span className="note">
                    {claim.evidence ? "Decided by" : "Closest passage, does not settle it"}:{" "}
                    {passage.title}
                  </span>
                  <span className="claim-quote">{passage.text.slice(0, 280)}</span>
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
