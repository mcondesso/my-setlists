<script lang="ts">
  import { ApiError } from "../lib/api";
  import { auth, setToken } from "../lib/auth.svelte";
  import { fetchMe, login } from "../lib/backend";
  import { navigate } from "../lib/router.svelte";

  let email = $state("");
  let password = $state("");
  let error = $state("");
  let submitting = $state(false);

  async function handleSubmit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    error = "";
    submitting = true;
    try {
      const { access_token } = await login(email, password);
      setToken(access_token);
      auth.user = await fetchMe();
      navigate("/setlists");
    } catch (err) {
      error = err instanceof ApiError ? err.message : "Could not log in.";
    } finally {
      submitting = false;
    }
  }
</script>

<form class="card narrow" onsubmit={handleSubmit}>
  <h1>Log in</h1>
  {#if error}<p class="error">{error}</p>{/if}
  <label>
    Email
    <input type="email" bind:value={email} required autocomplete="username" />
  </label>
  <label>
    Password
    <input type="password" bind:value={password} required autocomplete="current-password" />
  </label>
  <button type="submit" disabled={submitting}>{submitting ? "Logging in…" : "Log in"}</button>
  <p class="hint">No account? <a href="#/register">Register</a></p>
</form>
