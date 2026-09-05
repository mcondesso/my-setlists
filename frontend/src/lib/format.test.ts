import { describe, expect, it } from "vitest";
import { formatDuration, formatTotalDuration } from "./format";

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

describe("formatTotalDuration", () => {
  it("formats minutes only", () => {
    expect(formatTotalDuration(45 * 60 * 1000)).toBe("45 min");
  });

  it("formats hours and minutes", () => {
    expect(formatTotalDuration((60 + 23) * 60 * 1000)).toBe("1 hr 23 min");
  });

  it("omits the minutes part when it's a whole number of hours", () => {
    expect(formatTotalDuration(2 * 60 * 60 * 1000)).toBe("2 hr");
  });

  it("handles a sub-minute total", () => {
    expect(formatTotalDuration(20 * 1000)).toBe("under a minute");
  });

  it("handles zero", () => {
    expect(formatTotalDuration(0)).toBe("under a minute");
  });
});
