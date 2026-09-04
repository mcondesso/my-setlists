<script lang="ts">
  import { errorMessage } from "../lib/api";
  import { register } from "../lib/backend";
  import { completeLogin } from "../lib/session";
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
      await completeLogin(email, password);
      navigate("/setlists");
    } catch (err) {
      error = errorMessage(err, "Could not register.");
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
