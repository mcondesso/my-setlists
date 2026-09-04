<script lang="ts">
  import { onMount } from "svelte";
  import { auth, logout } from "./lib/auth.svelte";
  import { fetchMe } from "./lib/backend";
  import { navigate, router } from "./lib/router.svelte";
  import Login from "./pages/Login.svelte";
  import Register from "./pages/Register.svelte";
  import SetlistDetail from "./pages/SetlistDetail.svelte";
  import Setlists from "./pages/Setlists.svelte";

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

  function handleLogout(): void {
    logout();
    navigate("/login");
  }

  const setlistMatch = $derived(router.path.match(/^\/setlists\/([^/]+)$/));
</script>

<header>
  <a class="brand" href="#/setlists">My Setlists</a>
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

<main>
  {#if !auth.token}
    {#if router.path === "/register"}
      <Register />
    {:else}
      <Login />
    {/if}
  {:else if setlistMatch}
    <SetlistDetail id={setlistMatch[1]} />
  {:else}
    <Setlists />
  {/if}
</main>
