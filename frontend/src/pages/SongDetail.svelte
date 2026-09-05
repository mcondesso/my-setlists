<script lang="ts">
  import { errorMessage } from "../lib/api";
  import {
    addExistingSongToSetlist,
    fetchSetlists,
    fetchSong,
  } from "../lib/backend";
  import type { Setlist, Song } from "../lib/types";

  let { id }: { id: string } = $props();

  let song = $state<Song | null>(null);
  let mySetlists = $state<Setlist[]>([]);
  let selectedSetlistId = $state("");
  let loading = $state(true);
  let error = $state("");

  let adding = $state(false);
  let addMessage = $state("");

  // Bumped on every load() call; see SetlistDetail.svelte for why.
  let loadToken = 0;

  async function load(songId: string): Promise<void> {
    const thisLoad = ++loadToken;
    loading = true;
    error = "";
    addMessage = "";
    try {
      const [songResult, setlists] = await Promise.all([
        fetchSong(songId),
        fetchSetlists(200, 0),
      ]);
      if (thisLoad !== loadToken) return;
      song = songResult;
      mySetlists = setlists.filter((s) => s.is_owner);
      selectedSetlistId = mySetlists[0]?.id ?? "";
    } catch (err) {
      if (thisLoad !== loadToken) return;
      error = errorMessage(err, "Could not load song.");
    } finally {
      if (thisLoad === loadToken) loading = false;
    }
  }

  $effect(() => {
    load(id);
  });

  async function handleAdd(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (!song || !selectedSetlistId) return;
    adding = true;
    error = "";
    addMessage = "";
    try {
      await addExistingSongToSetlist(selectedSetlistId, song.id);
      const setlistName = mySetlists.find(
        (s) => s.id === selectedSetlistId,
      )?.name;
      addMessage = `Added to ${setlistName}.`;
    } catch (err) {
      error = errorMessage(err, "Could not add song to setlist.");
    } finally {
      adding = false;
    }
  }

  const linkLabels: Record<string, string> = {
    youtube: "Listen on YouTube",
    discogs: "View on Discogs",
    spotify: "Listen on Spotify",
    apple_music: "Listen on Apple Music",
    bandcamp: "View on Bandcamp",
  };
</script>

<a class="back" href="#/setlists">&larr; All setlists</a>

{#if loading}
  <p>Loading…</p>
{:else if !song}
  <p class="error">{error}</p>
{:else}
  <div class="song-hero">
    {#if song.thumbnail}
      <img src={song.thumbnail} alt="" />
    {/if}
    <div>
      <h1>{song.title}</h1>
      <p class="meta">
        {song.artist}{#if song.album}
          · {song.album}{/if}{#if song.release_year}
          · {song.release_year}{/if}
      </p>
    </div>
  </div>

  {#if error}<p class="error">{error}</p>{/if}

  {#if song.links.some((link) => link.url)}
    <ul class="grid">
      {#each song.links.filter((link) => link.url) as link (link.platform)}
        <li>
          <a
            class="card"
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {linkLabels[link.platform] ?? link.platform}
          </a>
        </li>
      {/each}
    </ul>
  {/if}

  <form class="card narrow" onsubmit={handleAdd}>
    <h2>Add to one of your setlists</h2>
    {#if mySetlists.length === 0}
      <p class="hint">You don't have any setlists yet.</p>
    {:else}
      <label>
        Setlist
        <select bind:value={selectedSetlistId}>
          {#each mySetlists as setlist (setlist.id)}
            <option value={setlist.id}>{setlist.name}</option>
          {/each}
        </select>
      </label>
      <button type="submit" disabled={adding}
        >{adding ? "Adding…" : "Add"}</button
      >
      {#if addMessage}<p class="hint">{addMessage}</p>{/if}
    {/if}
  </form>
{/if}
