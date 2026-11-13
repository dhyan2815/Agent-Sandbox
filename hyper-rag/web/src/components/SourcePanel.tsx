import { useEffect, useRef } from "react";
import type { Source, Span } from "../api";

export interface SourceView {
  title: string;
  subtitle: string;
  lines: Span[][];
  source: Source | null;
}

function Line({ spans, markFirst }: { spans: Span[]; markFirst: React.RefObject<HTMLElement | null> | null }) {
  const text = spans.map((s) => s.text).join(" ");
  const kind = text.startsWith("|") ? " table" : text.startsWith("#") ? " heading" : "";
  let first = markFirst;
  return (
    <p className={"line" + kind}>
      {spans.map((span, i) => {
        const content = kind === " heading" ? span.text.replace(/^#+\s*/, "") : span.text;
        const gap = i < spans.length - 1 ? " " : "";
        if (!span.hit) return <span key={i}>{content + gap}</span>;
        const ref = first;
        first = null; // only the first highlighted span of the line can be the scroll target
        return (
          <span key={i}>
            <mark ref={ref as React.RefObject<HTMLElement>}>{content}</mark>
            {gap}
          </span>
        );
      })}
    </p>
  );
}

export function SourcePanel({ view, onClose }: { view: SourceView; onClose: () => void }) {
  const { title, subtitle, lines, source } = view;
  const body = useRef<HTMLDivElement>(null);
  const firstHit = useRef<HTMLElement | null>(null);
  const firstHitLine = lines.findIndex((spans) => spans.some((s) => s.hit));

  useEffect(() => {
    if (body.current) body.current.scrollTop = 0;
    // With a page image on top, the image is what to look at first; without one, the passage.
    if (!source?.preview_url) firstHit.current?.scrollIntoView({ block: "center" });
  }, [view, source]);

  return (
    <aside className="source-panel" id="source-panel" aria-label="Source">
      <div className="source-head">
        <div>
          <h3 id="source-title">{title}</h3>
          <p id="source-sub">
            {subtitle}
            {source?.read_by_ocr && <span className="badge">read by OCR</span>}
          </p>
        </div>
        <button id="source-close" aria-label="Close source panel" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="source-body" id="source-body" ref={body}>
        {source && (
          <p>
            <a href={source.file_url} target="_blank" rel="noopener">
              {source.kind === "pdf" ? "Open the PDF at this page" : "Open the original file"}
            </a>
          </p>
        )}
        {source?.preview_url && (
          <>
            <h4>{source.kind === "pdf" ? "The page" : "The image"}</h4>
            <img src={source.preview_url} alt={`${title}, ${subtitle}`} loading="lazy" />
          </>
        )}
        {lines.length > 0 && <h4>Extracted text (cited passage highlighted)</h4>}
        {lines.map((spans, i) => (
          <Line key={i} spans={spans} markFirst={i === firstHitLine ? firstHit : null} />
        ))}
      </div>
    </aside>
  );
}
