<script lang="ts">
  let {
    ownerDisplayName,
    isPublic = false,
  }: { ownerDisplayName: string; isPublic?: boolean } = $props();
</script>

<p class="meta">
  by {ownerDisplayName}
  {#if isPublic}<span class="badge">Public</span>{/if}
</p>
