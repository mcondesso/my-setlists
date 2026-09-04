<script lang="ts">
  import { ApiError } from "../lib/api";
  import { auth, setToken } from "../lib/auth.svelte";
  import { fetchMe, login, register } from "../lib/backend";
  import { navigate } from "../lib/router.svelte";

  let email = $state("");
  let displayName = $state("");
  let password = $state("");
  let error = $state("");
  let submitting = $state(false);

  async function handleSubmit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    error = "";
    submitting = true;
    try {
      await register(email, displayName, password);
      const { access_token } = await login(email, password);
      setToken(access_token);
      auth.user = await fetchMe();
      navigate("/setlists");
    } catch (err) {
      error = err instanceof ApiError ? err.message : "Could not register.";
    } finally {
      submitting = false;
    }
  }
</script>

<form class="card narrow" onsubmit={handleSubmit}>
  <h1>Register</h1>
  {#if error}<p class="error">{error}</p>{/if}
  <label>
    Display name
    <input bind:value={displayName} required minlength="1" />
  </label>
  <label>
    Email
    <input type="email" bind:value={email} required autocomplete="username" />
  </label>
  <label>
    Password
    <input type="password" bind:value={password} required minlength="8" autocomplete="new-password" />
  </label>
  <button type="submit" disabled={submitting}>{submitting ? "Creating account…" : "Create account"}</button>
  <p class="hint">Already have an account? <a href="#/login">Log in</a></p>
</form>
