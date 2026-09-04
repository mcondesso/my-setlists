<script lang="ts">
  import { errorMessage } from "../lib/api";
  import { completeLogin } from "../lib/session";
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
      await completeLogin(email, password);
      navigate("/setlists");
    } catch (err) {
      error = errorMessage(err, "Could not log in.");
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
