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
        // api.ts already logs out on an invalid/expired token (401).
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
