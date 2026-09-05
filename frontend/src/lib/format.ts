/** Formats a duration in milliseconds as "M:SS" (or "H:MM:SS" past an hour). */
export function formatDuration(ms: number | null): string | null {
  if (ms === null || ms < 0) return null;
  const totalSeconds = Math.round(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const paddedSeconds = String(seconds).padStart(2, "0");

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${paddedSeconds}`;
  }
  return `${minutes}:${paddedSeconds}`;
}

/** Formats a total playback time as e.g. "1 hr 23 min", "45 min", or "under a minute". */
export function formatTotalDuration(ms: number): string {
  const totalMinutes = Math.round(ms / 60000);
  if (totalMinutes < 1) return "under a minute";

  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const parts = [];
  if (hours > 0) parts.push(`${hours} hr`);
  if (minutes > 0) parts.push(`${minutes} min`);
  return parts.join(" ");
}
