// Answer text -> segments: **bold** becomes strong text, [n] becomes a citation button.
// The answer is untrusted model output, so it is only ever rendered as text, never as HTML.

import type { Citation } from "./api";

export type Segment =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "cite"; citation: Citation };

export function segments(text: string, citations: Citation[]): Segment[] {
  const out: Segment[] = [];
  for (const part of text.split(/(\*\*[^*]+\*\*|\[\d+\])/)) {
    const cite = part.match(/^\[(\d+)\]$/);
    const citation = cite && citations.find((c) => c.number === Number(cite[1]));
    if (citation) out.push({ kind: "cite", citation });
    else if (part.startsWith("**") && part.endsWith("**") && part.length > 4)
      out.push({ kind: "bold", text: part.slice(2, -2) });
    else if (part) out.push({ kind: "text", text: part });
  }
  return out;
}

// What the agent is about to do after each step, shown while the answer is being worked on.
const NEXT_STEP: Record<string, string> = {
  condense: "searching the documents",
  route: "searching the documents",
  retrieve: "checking which passages are relevant",
  grade: "writing the answer",
  rewrite: "searching again with a new query",
  generate: "checking the answer against the sources",
};

export function nextStep(stepLine: string): string | null {
  if (stepLine.startsWith("decline")) return null;
  return NEXT_STEP[stepLine.split(":")[0]] ?? null;
}

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export const sizeText = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1048576).toFixed(1)} MB`;
