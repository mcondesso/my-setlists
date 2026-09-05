<script lang="ts">
  import { onMount } from "svelte";
  import { errorMessage } from "../lib/api";
  import { createSetlist, fetchSetlists } from "../lib/backend";
  import type { Setlist } from "../lib/types";
  import OwnerBadge from "../components/OwnerBadge.svelte";

  const PAGE_SIZE = 20;

  let setlists = $state<Setlist[]>([]);
  let offset = $state(0);
  // The API doesn't return a total count; a page shorter than PAGE_SIZE is
  // what tells us there's nothing more to load.
  let hasMore = $state(true);
  let loading = $state(true);
  let loadingMore = $state(false);
  let error = $state("");

  let newName = $state("");
  let newDescription = $state("");
  let newIsPublic = $state(false);
  let creating = $state(false);

  // GET /setlists/ already returns the caller's own setlists ahead of
  // public ones from others, so the list splits cleanly in two.
  const mySetlists = $derived(setlists.filter((s) => s.is_owner));
  const publicSetlists = $derived(setlists.filter((s) => !s.is_owner));

  onMount(async () => {
    try {
      const page = await fetchSetlists(PAGE_SIZE, 0);
      setlists = page;
      offset = page.length;
      hasMore = page.length === PAGE_SIZE;
    } catch (err) {
      error = errorMessage(err, "Could not load setlists.");
    } finally {
      loading = false;
    }
  });

  async function loadMore(): Promise<void> {
    loadingMore = true;
    error = "";
    try {
      const page = await fetchSetlists(PAGE_SIZE, offset);
      setlists = [...setlists, ...page];
      offset += page.length;
      hasMore = page.length === PAGE_SIZE;
    } catch (err) {
      error = errorMessage(err, "Could not load more setlists.");
    } finally {
      loadingMore = false;
    }
  }

  async function handleCreate(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    if (!newName.trim()) return;
    creating = true;
    error = "";
    try {
      const created = await createSetlist({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        is_public: newIsPublic,
      });
      // GET /setlists/ orders the current user's own setlists first, newest
      // first — prepending matches that without a round-trip to re-fetch
      // everything we already have. Bump offset so the next "Load more"
      // page boundary still lines up with what's now on screen.
      setlists = [created, ...setlists];
      offset += 1;
      newName = "";
      newDescription = "";
      newIsPublic = false;
    } catch (err) {
      error = errorMessage(err, "Could not create setlist.");
    } finally {
      creating = false;
    }
  }
</script>

<h1>Setlists</h1>
{#if error}<p class="error">{error}</p>{/if}

<form class="card narrow" onsubmit={handleCreate}>
  <h2>New setlist</h2>
  <label>
    Name
    <input bind:value={newName} required />
  </label>
  <label>
    Description
    <input bind:value={newDescription} />
  </label>
  <label class="checkbox">
    <input type="checkbox" bind:checked={newIsPublic} />
    Public
  </label>
  <button type="submit" disabled={creating}
    >{creating ? "Creating…" : "Create"}</button
  >
</form>

{#snippet setlistCard(setlist: Setlist)}
  <li>
    <a class="card" href={`#/setlists/${setlist.id}`}>
      <h3>
        {setlist.name}
        {#if setlist.is_library}<span class="badge">Library</span>{/if}
      </h3>
      {#if setlist.description}<p>{setlist.description}</p>{/if}
      <OwnerBadge
        ownerDisplayName={setlist.owner_display_name}
        isPublic={setlist.is_public}
      />
    </a>
  </li>
{/snippet}

{#if loading}
  <p>Loading…</p>
{:else if setlists.length === 0}
  <p>No setlists yet.</p>
{:else}
  {#if mySetlists.length > 0}
    <h2>My setlists</h2>
    <ul class="grid">
      {#each mySetlists as setlist (setlist.id)}
        {@render setlistCard(setlist)}
      {/each}
    </ul>
  {/if}

  {#if publicSetlists.length > 0}
    <h2 class="section-heading">Public setlists</h2>
    <ul class="grid">
      {#each publicSetlists as setlist (setlist.id)}
        {@render setlistCard(setlist)}
      {/each}
    </ul>
  {/if}

  {#if hasMore}
    <button class="ghost" onclick={loadMore} disabled={loadingMore}>
      {loadingMore ? "Loading…" : "Load more"}
    </button>
  {/if}
{/if}
