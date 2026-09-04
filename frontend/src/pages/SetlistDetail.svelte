<script lang="ts">
  import { errorMessage } from "../lib/api";
  import {
    addSongToSetlist,
    fetchSetlist,
    removeSongFromSetlist,
    searchSongs,
  } from "../lib/backend";
  import type { DiscogsSearchResult, SetlistWithEntries } from "../lib/types";
  import OwnerBadge from "../components/OwnerBadge.svelte";

  let { id }: { id: string } = $props();

  let setlist = $state<SetlistWithEntries | null>(null);
  let loading = $state(true);
  let error = $state("");

  let query = $state("");
  let results = $state<DiscogsSearchResult[]>([]);
  let searching = $state(false);
  let addingId = $state<string | null>(null);

  // Bumped on every load() call; a call whose result arrives after a newer
  // one has started is discarded instead of overwriting fresher data (can
  // happen if the user navigates from one setlist to another quickly and
  // the requests resolve out of order).
  let loadToken = 0;

  async function load(setlistId: string): Promise<void> {
    const thisLoad = ++loadToken;
    loading = true;
    error = "";
    try {
      const result = await fetchSetlist(setlistId);
      if (thisLoad !== loadToken) return;
      setlist = result;
    } catch (err) {
      if (thisLoad !== loadToken) return;
      error = errorMessage(err, "Could not load setlist.");
    } finally {
      if (thisLoad === loadToken) loading = false;
    }
  }

  $effect(() => {
    load(id);
    // Reset search state when navigating between setlists.
    query = "";
    results = [];
  });

  async function handleRemove(songId: string): Promise<void> {
    try {
      await removeSongFromSetlist(id, songId);
      if (setlist) {
        setlist.entries = setlist.entries.filter(
          (entry) => entry.song_id !== songId,
        );
      }
    } catch (err) {
      error = errorMessage(err, "Could not remove song.");
    }
  }

  async function handleSearch(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (!query.trim()) return;
    searching = true;
    error = "";
    try {
      results = await searchSongs(query.trim());
    } catch (err) {
      error = errorMessage(err, "Search failed.");
    } finally {
      searching = false;
    }
  }

  async function handleAdd(result: DiscogsSearchResult): Promise<void> {
    addingId = result.discogs_id;
    error = "";
    try {
      await addSongToSetlist(id, result);
      results = [];
      query = "";
      // The create response doesn't carry the entry's position/added_at or
      // the song's links, so re-fetch rather than fabricate an entry.
      await load(id);
    } catch (err) {
      error = errorMessage(err, "Could not add song.");
    } finally {
      addingId = null;
    }
  }
</script>

<a class="back" href="#/setlists">&larr; All setlists</a>

{#if loading}
  <p>Loading…</p>
{:else if !setlist}
  <p class="error">{error}</p>
{:else}
  <h1>{setlist.name}</h1>
  {#if setlist.description}<p>{setlist.description}</p>{/if}
  <OwnerBadge
    ownerDisplayName={setlist.owner_display_name}
    isPublic={setlist.is_public}
  />

  {#if error}<p class="error">{error}</p>{/if}

  <ol class="songs">
    {#each setlist.entries as entry (entry.song_id)}
      <li>
        {#if entry.song.thumbnail}
          <img src={entry.song.thumbnail} alt="" />
        {/if}
        <div class="song-info">
          <strong>{entry.song.title}</strong>
          <span>{entry.song.artist}</span>
        </div>
        <button class="ghost" onclick={() => handleRemove(entry.song_id)}
          >Remove</button
        >
      </li>
    {:else}
      <li class="empty">No songs yet — search below to add one.</li>
    {/each}
  </ol>

  <form class="card narrow search" onsubmit={handleSearch}>
    <h2>Add a song</h2>
    <input bind:value={query} placeholder="Search Discogs…" />
    <button type="submit" disabled={searching}
      >{searching ? "Searching…" : "Search"}</button
    >
  </form>

  {#if results.length > 0}
    <ul class="songs results">
      {#each results as result (result.discogs_id)}
        <li>
          {#if result.thumbnail}
            <img src={result.thumbnail} alt="" />
          {/if}
          <div class="song-info">
            <strong>{result.title}</strong>
            <span
              >{result.artist}{#if result.release_year}
                · {result.release_year}{/if}</span
            >
          </div>
          <button
            onclick={() => handleAdd(result)}
            disabled={addingId === result.discogs_id}
          >
            {addingId === result.discogs_id ? "Adding…" : "Add"}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
{/if}
