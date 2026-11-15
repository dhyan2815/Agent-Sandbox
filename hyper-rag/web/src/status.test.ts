import { describe, expect, it } from "vitest";
import { statusFrom } from "./status";

describe("statusFrom", () => {
  it("is down when there is no reply or the reply is not ok", () => {
    expect(statusFrom(null)).toBe("down");
    expect(statusFrom({ status: "starting" })).toBe("down");
  });
  it("is warming only while the models load", () => {
    expect(statusFrom({ status: "ok", warm: "warming" })).toBe("warming");
  });
  it("lets the page work once up, even if the warm-up failed or never ran", () => {
    expect(statusFrom({ status: "ok", warm: "ready" })).toBe("up");
    expect(statusFrom({ status: "ok", warm: "failed" })).toBe("up");
    expect(statusFrom({ status: "ok", warm: "idle" })).toBe("up");
  });
});
