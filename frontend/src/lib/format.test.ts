import { describe, expect, it } from "vitest";
import { formatDuration } from "./format";

describe("formatDuration", () => {
  it("formats seconds under a minute", () => {
    expect(formatDuration(45 * 1000)).toBe("0:45");
  });

  it("formats minutes and seconds, zero-padding seconds", () => {
    expect(formatDuration((3 * 60 + 5) * 1000)).toBe("3:05");
  });

  it("formats past an hour as H:MM:SS", () => {
    expect(formatDuration((60 * 60 + 5 * 60 + 9) * 1000)).toBe("1:05:09");
  });

  it("returns null for a missing duration", () => {
    expect(formatDuration(null)).toBeNull();
  });

  it("returns null for a negative duration", () => {
    expect(formatDuration(-1)).toBeNull();
  });
});
