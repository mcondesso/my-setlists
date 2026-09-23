<script lang="ts">
  import { onMount } from "svelte";
  import { auth, logout } from "./lib/auth.svelte";
  import { fetchMe } from "./lib/backend";
  import { navigate, router } from "./lib/router.svelte";
  import { startSessionRefresh } from "./lib/session";
  import Login from "./pages/Login.svelte";
  import Register from "./pages/Register.svelte";
  import SetlistDetail from "./pages/SetlistDetail.svelte";
  import Setlists from "./pages/Setlists.svelte";
  import SongDetail from "./pages/SongDetail.svelte";

  onMount(async () => {
    if (auth.token && !auth.user) {
      try {
        auth.user = await fetchMe();
      } catch {
        // Couldn't confirm the stored token is still good — for a 401 this
        // is a no-op (api.ts already logged out), but for any other failure
        // (network blip, 500) auth.token would otherwise stay set forever
        // with auth.user permanently null. Log out rather than leave the
        // app stuck half-authenticated; the user can just log back in.
        logout();
      }
    }
  });

  // Keeps an active session alive past ACCESS_TOKEN_EXPIRE_MINUTES instead
  // of hard-logging out mid-use; stopped when App unmounts (never, in
  // practice, but onMount's returned cleanup keeps this tidy either way).
  onMount(() => startSessionRefresh());

  function handleLogout(): void {
    logout();
    navigate("/login");
  }

  const setlistMatch = $derived(router.path.match(/^\/setlists\/([^/]+)$/));
  const songMatch = $derived(router.path.match(/^\/songs\/([^/]+)$/));
</script>

<header>
  <div class="brand-group">
    <a class="brand" href="#/setlists">My Setlists</a>
    <a
      class="github-link"
      href="https://github.com/mcondesso/my-setlists"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="View source on GitHub"
    >
      <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true">
        <path
          fill-rule="evenodd"
          d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"
        />
      </svg>
    </a>
  </div>
  <nav>
    {#if auth.token}
      <span class="who">{auth.user?.display_name ?? "…"}</span>
      <button class="ghost" onclick={handleLogout}>Log out</button>
    {:else}
      <a href="#/login">Log in</a>
      <a href="#/register">Register</a>
    {/if}
  </nav>
</header>

<main class:auth-layout={!auth.token}>
  {#if !auth.token}
    {#if router.path === "/register"}
      <Register />
    {:else}
      <Login />
    {/if}
  {:else if setlistMatch}
    <SetlistDetail id={setlistMatch[1]} />
  {:else if songMatch}
    <SongDetail id={songMatch[1]} />
  {:else}
    <Setlists />
  {/if}
</main>
