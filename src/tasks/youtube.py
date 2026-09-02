"""Background tasks for enriching song data with YouTube links."""

import logging
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from src.models.song import Song
from src.models.song_link import Platform, SongLink
from src.services.youtube import find_top_youtube_video

logger = logging.getLogger(__name__)


def fetch_and_save_youtube_link(song_id: UUID, engine: Engine) -> None:
    """
    Find the most-viewed YouTube video for a song and save it to song_links.

    Runs as a background task after the request that created the song, so it
    opens its own session. `engine` is the bind of that request's session
    (passed by the caller) so the task writes to the same database.

    Skips the lookup if a YouTube link already exists for the song.
    Logs a warning and exits silently if no video is found or an error occurs.
    """
    try:
        with Session(engine) as session:
            song = session.get(Song, song_id)
            if not song:
                logger.warning("Song %s not found, skipping YouTube lookup", song_id)
                return

            existing = session.exec(
                select(SongLink).where(
                    SongLink.song_id == song_id,
                    SongLink.platform == Platform.YOUTUBE,
                )
            ).first()

            if existing:
                logger.info("YouTube link already exists for song %s, skipping", song_id)
                return

            result = find_top_youtube_video(artist=song.artist, title=song.title)

            if not result:
                logger.warning(
                    "No YouTube results found for '%s' by '%s'",
                    song.title,
                    song.artist,
                )
                return

            link = SongLink(
                song_id=song_id,
                platform=Platform.YOUTUBE,
                external_id=result["video_id"],
                url=result["url"],
            )
            session.add(link)
            session.commit()
            logger.info(
                "Saved YouTube link for '%s' by '%s': %s",
                song.title,
                song.artist,
                result["url"],
            )

    except Exception:
        logger.exception("Unexpected error during YouTube lookup for song %s", song_id)
