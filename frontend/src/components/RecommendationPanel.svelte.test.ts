import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Recommendation } from "../lib/types";

vi.mock("../lib/backend", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/backend")>();
  return {
    ...actual,
    fetchRecommendation: vi.fn(),
    refreshRecommendation: vi.fn(),
  };
});

import { fetchRecommendation, refreshRecommendation } from "../lib/backend";
import RecommendationPanel from "./RecommendationPanel.svelte";

function recommendation(
  overrides: Partial<Recommendation> = {},
): Recommendation {
  return {
    status: "ready",
    title: "Dancing Queen",
    artist: "ABBA",
    album: "Arrival",
    release_year: 1976,
    duration_ms: 231000,
    thumbnail: null,
    discogs_id: "1-A1",
    discogs_url: "https://www.discogs.com/master/1",
    ...overrides,
  };
}

const pending = recommendation({
  status: "pending",
  title: null,
  artist: null,
  discogs_id: null,
});

function renderPanel(
  props: Partial<{
    isOwner: boolean;
    hasSongs: boolean;
    recommendation: Recommendation | null;
  }> = {},
) {
  const onadd = vi.fn();
  render(RecommendationPanel, {
    props: {
      setlistId: "s1",
      isOwner: true,
      hasSongs: true,
      recommendation: recommendation(),
      onadd,
      ...props,
    },
  });
  return { onadd };
}

describe("RecommendationPanel", () => {
  beforeEach(() => {
    vi.mocked(fetchRecommendation).mockReset();
    vi.mocked(refreshRecommendation).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("asks for a song first when the setlist is empty", () => {
    renderPanel({ hasSongs: false, recommendation: null });

    expect(
      screen.getByText("Add a song to enable recommendations."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Refresh" }),
    ).not.toBeInTheDocument();
  });

  it("shows a ready recommendation and adds it as a Discogs result", async () => {
    const { onadd } = renderPanel();

    expect(screen.getByText("Dancing Queen")).toBeInTheDocument();
    expect(screen.getByText("ABBA· 1976· 3:51")).toBeInTheDocument();

    await fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(onadd).toHaveBeenCalledWith(
      expect.objectContaining({
        discogs_id: "1-A1",
        title: "Dancing Queen",
        artist: "ABBA",
        duration_ms: 231000,
      }),
    );
  });

  it("disables Add and hides Refresh for someone who doesn't own the setlist", () => {
    renderPanel({ isOwner: false });

    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Refresh" }),
    ).not.toBeInTheDocument();
  });

  it.each([
    ["not_found", recommendation({ status: "not_found", title: null })],
    ["failed", recommendation({ status: "failed", title: null })],
    ["never generated", null],
  ])("asks the owner to refresh when there is none (%s)", (_, rec) => {
    renderPanel({ recommendation: rec });

    expect(
      screen.getByText("No recommendations, try refreshing."),
    ).toBeInTheDocument();
  });

  it("tells a viewer there are none yet, without a refresh prompt", () => {
    renderPanel({
      isOwner: false,
      recommendation: recommendation({ status: "not_found", title: null }),
    });

    expect(screen.getByText("No recommendations yet.")).toBeInTheDocument();
  });

  it("refreshes, polls while pending, then shows the new song", async () => {
    vi.useFakeTimers();
    vi.mocked(refreshRecommendation).mockResolvedValue(pending);
    vi.mocked(fetchRecommendation)
      .mockResolvedValueOnce(pending)
      .mockResolvedValueOnce(
        recommendation({ title: "Africa", artist: "Toto", discogs_id: "2-A1" }),
      );
    renderPanel();

    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(refreshRecommendation).toHaveBeenCalledWith("s1");
    expect(screen.getByText("Finding a recommendation…")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(2000);
    expect(screen.getByText("Finding a recommendation…")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(2000);
    expect(screen.getByText("Africa")).toBeInTheDocument();
    expect(fetchRecommendation).toHaveBeenCalledTimes(2);
  });

  it("stops polling after a minute and offers a refresh", async () => {
    vi.useFakeTimers();
    vi.mocked(fetchRecommendation).mockResolvedValue(pending);
    renderPanel({ recommendation: pending });

    await vi.advanceTimersByTimeAsync(60_000);

    expect(fetchRecommendation).toHaveBeenCalledTimes(30);
    expect(
      screen.getByText("No recommendations, try refreshing."),
    ).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(fetchRecommendation).toHaveBeenCalledTimes(30);
  });

  it("shows the server's message when a refresh is rejected", async () => {
    const { ApiError } = await import("../lib/api");
    vi.mocked(refreshRecommendation).mockRejectedValue(
      new ApiError(429, "Rate limit exceeded: 5 per 1 minute"),
    );
    renderPanel();

    await fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(
      await screen.findByText("Rate limit exceeded: 5 per 1 minute"),
    ).toBeInTheDocument();
  });
});
