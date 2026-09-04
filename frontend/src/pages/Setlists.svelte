<script lang="ts">
  import { onMount } from "svelte";
  import { errorMessage } from "../lib/api";
  import { createSetlist, fetchSetlists } from "../lib/backend";
  import type { Setlist } from "../lib/types";
  import OwnerBadge from "../components/OwnerBadge.svelte";

  let setlists = $state<Setlist[]>([]);
  let loading = $state(true);
  let error = $state("");

  let newName = $state("");
  let newDescription = $state("");
  let newIsPublic = $state(false);
  let creating = $state(false);

  async function load(): Promise<void> {
    loading = true;
    try {
      setlists = await fetchSetlists();
    } catch (err) {
      error = errorMessage(err, "Could not load setlists.");
    } finally {
      loading = false;
    }
  }

  onMount(load);

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
      // everything we already have.
      setlists = [created, ...setlists];
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
  <button type="submit" disabled={creating}>{creating ? "Creating…" : "Create"}</button>
</form>

{#if loading}
  <p>Loading…</p>
{:else if setlists.length === 0}
  <p>No setlists yet.</p>
{:else}
  <ul class="grid">
    {#each setlists as setlist (setlist.id)}
      <li>
        <a class="card" href={`#/setlists/${setlist.id}`}>
          <h3>
            {setlist.name}
            {#if setlist.is_library}<span class="badge">Library</span>{/if}
          </h3>
          {#if setlist.description}<p>{setlist.description}</p>{/if}
          <OwnerBadge ownerDisplayName={setlist.owner_display_name} isPublic={setlist.is_public} />
        </a>
      </li>
    {/each}
  </ul>
{/if}
