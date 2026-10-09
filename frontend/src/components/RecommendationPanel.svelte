<script lang="ts">
  import { errorMessage } from "../lib/api";
  import { fetchRecommendation, refreshRecommendation } from "../lib/backend";
  import { formatDuration } from "../lib/format";
  import type { DiscogsSearchResult, Recommendation } from "../lib/types";

  // The backend debounces, then calls Gemini and up to 3 Discogs lookups —
  // typically 5-15s. Give up after a minute rather than spin forever.
  const POLL_INTERVAL_MS = 2000;
  const MAX_POLLS = 30;

  let {
    setlistId,
    isOwner,
    hasSongs,
    recommendation = $bindable(),
    adding = false,
    onadd,
  }: {
    setlistId: string;
    isOwner: boolean;
    hasSongs: boolean;
    recommendation: Recommendation | null;
    adding?: boolean;
    onadd: (result: DiscogsSearchResult) => void;
  } = $props();

  let refreshing = $state(false);
  let stalled = $state(false);
  let error = $state("");

  const pending = $derived(recommendation?.status === "pending" && !stalled);
  const ready = $derived(
    recommendation?.status === "ready" &&
      !!recommendation.title &&
      !!recommendation.artist &&
      !!recommendation.discogs_id,
  );

  // Poll while the backend is still working on a recommendation.
  $effect(() => {
    if (recommendation?.status !== "pending") return;
    stalled = false;
    let polls = 0;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll(): Promise<void> {
      polls += 1;
      try {
        const latest = await fetchRecommendation(setlistId);
        if (cancelled) return;
        if (latest?.status !== "pending") {
          recommendation = latest;
          return;
        }
      } catch {
        if (cancelled) return;
        // A failed poll is retried like a still-pending one.
      }
      if (polls >= MAX_POLLS) {
        stalled = true;
        return;
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    }

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  });

  async function handleRefresh(): Promise<void> {
    refreshing = true;
    error = "";
    try {
      recommendation = await refreshRecommendation(setlistId);
    } catch (err) {
      error = errorMessage(err, "Could not refresh the recommendation.");
    } finally {
      refreshing = false;
    }
  }

  function handleAdd(): void {
    if (!recommendation || !ready) return;
    onadd({
      discogs_id: recommendation.discogs_id!,
      title: recommendation.title!,
      artist: recommendation.artist!,
      album: recommendation.album,
      release_year: recommendation.release_year,
      discogs_url: recommendation.discogs_url,
      thumbnail: recommendation.thumbnail,
      duration_ms: recommendation.duration_ms,
    });
  }
</script>

<section class="recommendation">
  <div class="section-title">
    <h2>Recommended</h2>
    {#if isOwner && hasSongs}
      <button
        class="ghost"
        onclick={handleRefresh}
        disabled={refreshing || pending}
      >
        {refreshing ? "Refreshing…" : "Refresh"}
      </button>
    {/if}
  </div>

  {#if !hasSongs}
    <p class="hint">Add a song to enable recommendations.</p>
  {:else if pending}
    <p class="hint">Finding a recommendation…</p>
  {:else if ready && recommendation}
    <ul class="songs results">
      <li>
        {#if recommendation.thumbnail}
          <img src={recommendation.thumbnail} alt="" />
        {/if}
        <div class="song-info">
          <strong>{recommendation.title}</strong>
          <span
            >{recommendation.artist}{#if recommendation.release_year}
              · {recommendation.release_year}{/if}{#if formatDuration(recommendation.duration_ms)}
              · {formatDuration(recommendation.duration_ms)}{/if}</span
          >
        </div>
        <button
          onclick={handleAdd}
          disabled={!isOwner || adding}
          title={isOwner ? undefined : "Only the setlist's owner can add songs"}
        >
          {adding ? "Adding…" : "Add"}
        </button>
      </li>
    </ul>
  {:else}
    <p class="hint">
      {isOwner
        ? "No recommendations, try refreshing."
        : "No recommendations yet."}
    </p>
  {/if}

  {#if error}<p class="error">{error}</p>{/if}
</section>
