const DEFAULT_PATH = "/setlists";
const AUTH_PATHS = new Set(["/login", "/register"]);

function normalize(hash: string): string {
  const path = hash.replace(/^#/, "");
  return path || DEFAULT_PATH;
}

export const router = $state({ path: normalize(window.location.hash) });

// Where to send a visitor once they log in or register: the page they were
// on when they headed to /login or /register.
let returnPath = DEFAULT_PATH;

window.addEventListener("hashchange", () => {
  const previous = router.path;
  router.path = normalize(window.location.hash);
  // Hopping between /login and /register keeps the original page.
  if (AUTH_PATHS.has(router.path) && !AUTH_PATHS.has(previous)) {
    returnPath = previous;
  }
});

export function navigate(path: string): void {
  window.location.hash = path;
}

/** The page to return to after logging in or registering; resets it. */
export function takeReturnPath(): string {
  const path = returnPath;
  returnPath = DEFAULT_PATH;
  return path;
}
