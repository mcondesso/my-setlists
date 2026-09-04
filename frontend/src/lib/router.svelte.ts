function normalize(hash: string): string {
  const path = hash.replace(/^#/, "");
  return path || "/setlists";
}

export const router = $state({ path: normalize(window.location.hash) });

window.addEventListener("hashchange", () => {
  router.path = normalize(window.location.hash);
});

export function navigate(path: string): void {
  window.location.hash = path;
}
