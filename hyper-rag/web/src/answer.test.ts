import { describe, expect, it } from "vitest";
import type { Citation } from "./api";
import { nextStep, plural, segments, sizeText } from "./answer";

const cite = (number: number): Citation => ({
  number,
  title: `Source ${number}`,
  url: "",
  chunk_id: `abc/1#${number}`,
  doc_id: "abc/1",
  text: "",
});

describe("segments", () => {
  it("turns [n] into citations, **x** into bold and keeps the rest as text", () => {
    const parts = segments("It takes **two days** [1] or less [2].", [cite(1), cite(2)]);
    expect(parts.map((p) => p.kind)).toEqual(["text", "bold", "text", "cite", "text", "cite", "text"]);
    expect(parts[1]).toEqual({ kind: "bold", text: "two days" });
  });

  it("leaves a number with no such citation as plain text", () => {
    expect(segments("See [3].", [cite(1)])).toEqual([
      { kind: "text", text: "See " },
      { kind: "text", text: "[3]" },
      { kind: "text", text: "." },
    ]);
  });

  it("never produces markup from the answer text", () => {
    const parts = segments("<img src=x onerror=alert(1)>", []);
    expect(parts).toEqual([{ kind: "text", text: "<img src=x onerror=alert(1)>" }]);
  });
});

describe("helpers", () => {
  it("names the next step, and nothing after a decline", () => {
    expect(nextStep("retrieve: 5 passages")).toBe("checking which passages are relevant");
    expect(nextStep("decline: out of scope")).toBeNull();
    expect(nextStep("check: grounded")).toBeNull();
  });

  it("pluralises and sizes", () => {
    expect(plural(1, "file")).toBe("1 file");
    expect(plural(2, "file")).toBe("2 files");
    expect(sizeText(500)).toBe("1 KB");
    expect(sizeText(3 * 1048576)).toBe("3.0 MB");
  });
});
