import { useRef, useState } from "react";
import { plural, sizeText } from "../answer";
import { type Collection, type Config, type FileRecord, api } from "../api";

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
  const picker = useRef<HTMLInputElement>(null);
  const slug = collection.slug;

  const setItem = (id: number, status: QueueItem["status"], text: string) =>
    setQueue((items) => items.map((item) => (item.id === id ? { ...item, status, text } : item)));

  // One file at a time: each upload is parsed and indexed before the reply comes back.
  const upload = async (files: File[]) => {
    for (const file of files) {
      const id = Date.now() + Math.random();
      setQueue((items) => [{ id, name: file.name, status: "wait", text: "Reading and indexing…" }, ...items]);
      const extension = (file.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
      if (file.size > config.max_upload_mb * 1048576) {
        setItem(id, "fail", `Larger than the ${config.max_upload_mb} MB limit`);
        continue;
      }
      try {
        const form = new FormData();
        form.append("file", file);
        const record = await api<FileRecord>(`/collections/${slug}/files`, { method: "POST", body: form });
        const read = `${plural(record.chunks, "passage")} from ${plural(record.report.units, record.report.unit_name)}`;
        setItem(id, "ok", record.duplicate ? "Already in this collection" : `${record.replaced ? "Replaced. " : ""}${read}`);
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
                        <td>
                          <button className="quiet" onClick={() => remove(file)}>
                            Remove
                          </button>
                        </td>
                      </tr>,
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
