import { describe, expect, it } from "vitest";
import { sseReader } from "./api";

describe("sseReader", () => {
  it("joins messages split across pieces and ignores non-data blocks", () => {
    const read = sseReader();
    expect(read('data: {"type":"step","te')).toEqual([]);
    expect(read('xt":"retrieve: 5"}\n\n: comment\n\ndata: {"type":"ev')).toEqual([
      { type: "step", text: "retrieve: 5" },
    ]);
    expect(read('ent","t":"r.dense"}\n\n')).toEqual([{ type: "event", t: "r.dense" }]);
  });

  it("returns several messages from one piece, in order", () => {
    const read = sseReader();
    const piece = 'data: {"type":"step","text":"a"}\n\ndata: {"type":"step","text":"b"}\n\n';
    expect(read(piece).map((m) => (m.type === "step" ? m.text : ""))).toEqual(["a", "b"]);
  });
});
