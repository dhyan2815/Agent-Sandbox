import { useState } from "react";
import { postJson } from "../api";

interface Exported {
  format: string;
  filename: string;
  text: string;
}

/** Take a saved answer out of the app: copy or download it as Markdown, or draft a post. */
export function ExportMenu({ slug, runId }: { slug: string; runId: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [draft, setDraft] = useState<Exported | null>(null);

  const fetchExport = async (format: "markdown" | "linkedin") => {
    setBusy(true);
    setMessage("");
    try {
      return await postJson<Exported>(`/collections/${slug}/export`, { run_id: runId, format });
    } catch (failure) {
      setMessage((failure as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  };

  const copy = async (text: string, done: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage(done);
    } catch {
      setMessage("Copying was blocked by the browser. Use Download instead.");
    }
  };

  const copyMarkdown = async () => {
    const result = await fetchExport("markdown");
    if (result) await copy(result.text, "Copied as Markdown. Paste it into Notion or any editor.");
  };

  const download = async () => {
    const result = await fetchExport("markdown");
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.text], { type: "text/markdown" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = result.filename;
    link.click();
    URL.revokeObjectURL(url);
    setMessage(`Saved ${result.filename}`);
  };

  const outline = async () => {
    const result = await fetchExport("linkedin");
    if (result) {
      setDraft(result);
      setMessage("");
    }
  };

  return (
    <div className="export" data-testid="export-menu">
      <span className="note">Export:</span>
      <button className="quiet" disabled={busy} onClick={copyMarkdown}>
        Copy as Markdown
      </button>
      <button className="quiet" disabled={busy} onClick={download}>
        Download .md
      </button>
      <button className="quiet" disabled={busy} onClick={outline} title="Uses one model request">
        LinkedIn outline
      </button>
      {message && (
        <span className="note" role="status">
          {message}
        </span>
      )}
      {draft && (
        <div className="export-draft">
          <textarea readOnly rows={9} aria-label="LinkedIn post outline" value={draft.text} />
          <p className="note">
            A draft written from this answer only. It is not checked against the sources again:
            read it against them before you post.
          </p>
          <button className="quiet" onClick={() => copy(draft.text, "Copied the outline.")}>
            Copy outline
          </button>
        </div>
      )}
    </div>
  );
}
