import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

interface PageCell {
  number: number;
  route: string;
  reason: string;
  chars: number;
  window: number;
  done: boolean;
}

const ROUTE_NAMES: Record<string, string> = {
  "fast-text": "plain text",
  layout: "tables or columns",
  images: "images",
  ocr: "scanned (OCR)",
  skip: "skipped",
};

/** One cell per page, coloured by how it is read, filled in as its window commits. */
export function PageGrid({ slug, fileId, live }: { slug: string; fileId: string; live: boolean }) {
  const grid = useQuery({
    queryKey: ["pages", slug, fileId],
    queryFn: () => api<{ pages: PageCell[]; window_pages: number | null }>(`/collections/${slug}/files/${fileId}/pages`),
    refetchInterval: live ? 1500 : false,
  });
  const pages = grid.data?.pages ?? [];
  if (!pages.length) return null;
  const counts = new Map<string, number>();
  for (const page of pages) counts.set(page.route, (counts.get(page.route) ?? 0) + 1);
  return (
    <div className="page-grid" data-testid="page-grid">
      <div className="cells" role="list" aria-label="Pages">
        {pages.map((page) => (
          <span
            key={page.number}
            role="listitem"
            className={`cell ${page.route} ${page.done ? "done" : "todo"}`}
            title={`Page ${page.number}: ${ROUTE_NAMES[page.route] ?? page.route}${page.reason ? ` (${page.reason})` : ""}, ${page.chars} characters in the text layer, ${page.done ? "searchable" : "not read yet"}`}
          />
        ))}
      </div>
      <p className="legend">
        {[...counts.entries()].map(([route, count]) => (
          <span key={route}>
            <span className={`cell ${route} done`} aria-hidden="true" /> {count} {ROUTE_NAMES[route] ?? route}
          </span>
        ))}
        <span>
          <span className="cell todo" aria-hidden="true" /> not read yet
        </span>
      </p>
    </div>
  );
}
