import { useRef, useState } from "react";
import { plural, sizeText } from "../answer";
import { type Collection, type Config, type FileRecord, api, isReading, uploadResumable } from "../api";
import { PageGrid } from "../viz/PageGrid";

interface QueueItem {
  id: number;
  name: string;
  status: "wait" | "ok" | "fail";
  text: string;
}

interface Props {
  collection: Collection;
  config: Config;
  onChanged: () => Promise<unknown>;
}

const HEAD = ["File", "Type", "Read as", "Tables", "Images (text found)", "By OCR", "Passages", "Size", "Took", ""];
const NUMERIC = new Set([3, 4, 5, 6, 7, 8]);

export function FilesView({ collection, config, onChanged }: Props) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [over, setOver] = useState(false);
  const [gridOpen, setGridOpen] = useState<Set<string>>(new Set());
  const toggleGrid = (id: string) =>
    setGridOpen((open) => {
      const next = new Set(open);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const picker = useRef<HTMLInputElement>(null);
  const slug = collection.slug;

  const setItem = (id: number, status: QueueItem["status"], text: string) =>
    setQueue((items) => items.map((item) => (item.id === id ? { ...item, status, text } : item)));

  // Files are sent in parts, one file at a time; reading them happens on the server in the
  // background, and the table below follows its progress.
  const upload = async (files: File[]) => {
    for (const file of files) {
      const id = Date.now() + Math.random();
      setQueue((items) => [{ id, name: file.name, status: "wait", text: "Uploading…" }, ...items]);
      const extension = (file.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
      try {
        const record = await uploadResumable(slug, file, (fraction) =>
          setItem(id, "wait", `Uploading ${Math.floor(fraction * 100)}%`),
        );
        setItem(id, "ok", record.duplicate ? "Already in this collection" : "Uploaded; reading it now");
      } catch (error) {
        const unsupported = extension && !config.extensions.includes(extension);
        setItem(id, "fail", unsupported ? `${extension} files are not supported` : (error as Error).message);
      }
      await onChanged();
    }
  };

  const remove = async (file: FileRecord) => {
    if (!confirm(`Remove "${file.name}" from this collection?`)) return;
    await api(`/collections/${slug}/files/${file.id}`, { method: "DELETE" });
    await onChanged();
  };

  const stop = (event: React.DragEvent) => event.preventDefault();

  return (
    <div className="view" id="files-view">
      <div className="pad">
        <div
          id="drop"
          className={over ? "over" : ""}
          onDragEnter={(e) => (stop(e), setOver(true))}
          onDragOver={(e) => (stop(e), setOver(true))}
          onDragLeave={(e) => (stop(e), setOver(false))}
          onDrop={(e) => {
            stop(e);
            setOver(false);
            upload([...e.dataTransfer.files]);
          }}
        >
          <strong>Drop files here</strong> or{" "}
          <button id="choose" type="button" onClick={() => picker.current?.click()}>
            Choose files
          </button>
          <p id="accepted">
            PDF, Word, PowerPoint, Excel, images, text, Markdown, HTML and CSV, up to{" "}
            {config.max_upload_mb} MB each. Tables are kept as tables; images and scanned pages
            are read by OCR on this machine.
          </p>
          <input
            id="picker"
            ref={picker}
            type="file"
            multiple
            hidden
            accept={config.extensions.join(",")}
            onChange={(event) => {
              upload([...(event.target.files ?? [])]);
              event.target.value = "";
            }}
          />
        </div>
        <ul id="queue" aria-live="polite">
          {queue.map((item) => (
            <li key={item.id}>
              <span>{item.name}</span>
              <span className={item.status}>{item.text}</span>
            </li>
          ))}
        </ul>
        {collection.files.length > 0 && (
          <div id="files-table">
            <h3 className="section">What was extracted</h3>
            <p className="note">
              Check this before trusting answers: a file that shows 0 passages, or images with no
              text found, contributes nothing to search.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {HEAD.map((label, i) => (
                      <th key={i} className={NUMERIC.has(i) ? "num" : ""}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {collection.files.map((file) => {
                    const r = file.report;
                    if (!r || isReading(file) || file.status === "failed") {
                      return <ProgressRow key={file.id} slug={slug} file={file} span={HEAD.length} onRemove={() => remove(file)} />;
                    }
                    return [
                      <tr key={file.id}>
                        <td className="name">
                          <a href={`/collections/${slug}/files/${file.id}`} target="_blank" rel="noopener">
                            {file.name}
                          </a>
                        </td>
                        <td>{r.kind}</td>
                        <td>{plural(r.units, r.unit_name)}</td>
                        <td className="num">{r.tables}</td>
                        <td className="num">{r.images ? `${r.images} (${r.images_with_text})` : "0"}</td>
                        <td className="num">{r.ocr_units ? plural(r.ocr_units, r.unit_name) : "0"}</td>
                        <td className="num">{file.chunks}</td>
                        <td className="num">{sizeText(file.size)}</td>
                        <td className="num">{file.seconds} s</td>
                        <td className="actions">
                          {file.kind === "pdf" && (
                            <button
                              className="quiet"
                              aria-expanded={gridOpen.has(file.id)}
                              onClick={() => toggleGrid(file.id)}
                            >
                              Pages
                            </button>
                          )}
                          <button className="quiet" onClick={() => remove(file)}>
                            Remove
                          </button>
                        </td>
                      </tr>,
                      gridOpen.has(file.id) ? (
                        <tr key={`${file.id}-grid`} className="grid-row">
                          <td colSpan={HEAD.length}>
                            <PageGrid slug={slug} fileId={file.id} live={false} />
                          </td>
                        </tr>
                      ) : null,
                      ...r.warnings.map((warning, i) => (
                        <tr key={`${file.id}-w${i}`} className="warn">
                          <td colSpan={HEAD.length}>{warning}</td>
                        </tr>
                      )),
                    ];
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const ROUTE_LABELS: Record<string, string> = {
  "fast-text": "plain text",
  layout: "with tables or columns",
  images: "with images",
  ocr: "scanned",
  skip: "blank or repeated",
};

/** A file still being read (or that failed): progress, the X-ray estimate, or the reason. */
function ProgressRow({ slug, file, span, onRemove }: { slug: string; file: FileRecord; span: number; onRemove: () => void }) {
  const total = file.pages_total ?? 0;
  const done = file.pages_done ?? 0;
  const share = total ? Math.floor((100 * done) / total) : 0;
  const routes = Object.entries(file.xray?.routes ?? {})
    .filter(([, n]) => n > 0)
    .map(([route, n]) => `${n.toLocaleString()} ${ROUTE_LABELS[route] ?? route}`)
    .join(" · ");
  const estimate = file.xray?.estimate_seconds;
  let status: string;
  if (file.status === "failed") status = `Could not be read: ${file.error ?? "unknown error"}`;
  else if (file.status === "queued") status = "Waiting to be read";
  else if (total) status = `Reading ${share}% · ${done.toLocaleString()} of ${total.toLocaleString()} pages searchable`;
  else status = "Reading…";
  return (
    <>
      <tr className="reading">
        <td className="name">
          <a href={`/collections/${slug}/files/${file.id}`} target="_blank" rel="noopener">
            {file.name}
          </a>
        </td>
        <td colSpan={span - 2}>
          <div className={file.status === "failed" ? "error" : ""}>{status}</div>
          {total > 0 && file.status !== "failed" && (
            <div className="bar" role="progressbar" aria-valuenow={share} aria-valuemin={0} aria-valuemax={100} aria-label={`${file.name} read`}>
              <span style={{ width: `${share}%` }} />
            </div>
          )}
          {routes && (
            <p className="note">
              {routes}
              {estimate ? ` (about ${formatSeconds(estimate)} of work)` : ""}
            </p>
          )}
          {file.xray?.warning && <p className="note">{file.xray.warning}</p>}
          {file.kind === "pdf" && file.status !== "failed" && (
            <PageGrid slug={slug} fileId={file.id} live={isReading(file)} />
          )}
        </td>
        <td>
          <button className="quiet" onClick={onRemove}>
            Remove
          </button>
        </td>
      </tr>
    </>
  );
}

function formatSeconds(seconds: number): string {
  if (seconds < 90) return `${Math.max(1, Math.round(seconds))} s`;
  if (seconds < 5400) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} h`;
}
