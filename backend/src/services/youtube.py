"""YouTube search service for finding video links for songs."""

from youtube_search import YoutubeSearch


def find_top_youtube_video(artist: str, title: str) -> dict | None:
    """
    Search YouTube for a song and return the video with the most views.

    Returns a dict with 'video_id' and 'url', or None if no results found.
    """
    query = f"{artist} {title}"
    results = YoutubeSearch(query, max_results=5).to_dict()

    if not results:
        return None

    top = max(results, key=lambda r: _parse_views(r.get("views", "0")))

    video_id = top.get("id")
    if not video_id:
        return None

    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def _parse_views(views_str: str) -> int:
    """
    Parse a view count string into an integer.

    YouTube returns views as strings like '1,234,567 views' or '1.2M views'.
    Returns 0 if the string cannot be parsed.
    """
    if not views_str:
        return 0

    cleaned = views_str.lower().replace(" views", "").replace(",", "").strip()

    try:
        if cleaned.endswith("m"):
            return int(float(cleaned[:-1]) * 1_000_000)
        if cleaned.endswith("k"):
            return int(float(cleaned[:-1]) * 1_000)
        return int(cleaned)
    except (ValueError, TypeError):
        return 0
