"""Background task that picks a song recommendation for a setlist."""

import logging
import time
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from src.models.recommendation import RecommendationStatus, SetlistRecommendation
from src.models.setlist import SetlistEntry
from src.models.song import Song
from src.services.discogs import DiscogsSearchResult, find_track
from src.services.gemini import GeminiNotConfiguredError, suggest_songs

logger = logging.getLogger(__name__)

# Adding several songs in a row queues one run per change. Waiting a moment
# lets every run but the last notice it has been superseded before it
# spends a Gemini call.
DEBOUNCE_SECONDS = 3.0


def queue_recommendation_update(
    setlist_id: UUID, session: Session, background_tasks: BackgroundTasks
) -> SetlistRecommendation:
    """
    Mark the setlist's recommendation as pending and queue a run to replace
    it. Commits. Call it after the change that prompted it is committed.

    The previous recommendation's fields are kept while pending, so the run
    can avoid suggesting the same song again.
    """
    recommendation = session.get(SetlistRecommendation, setlist_id) or SetlistRecommendation(
        setlist_id=setlist_id, status=RecommendationStatus.PENDING
    )
    recommendation.status = RecommendationStatus.PENDING
    recommendation.request_id = uuid4()
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)

    background_tasks.add_task(
        update_recommendation, setlist_id, recommendation.request_id, session.get_bind()
    )
    return recommendation


def update_recommendation(setlist_id: UUID, request_id: UUID, engine: Engine) -> None:
    """
    Ask Gemini for 3 songs that fit the setlist and store the first one that
    can be found on Discogs.

    Runs after the response, in its own sessions. Does nothing if a newer
    request has superseded `request_id` by the time it starts or finishes.
    Failures are logged and stored as FAILED, never raised.
    """
    time.sleep(DEBOUNCE_SECONDS)

    with Session(engine) as session:
        recommendation = session.get(SetlistRecommendation, setlist_id)
        if recommendation is None or recommendation.request_id != request_id:
            return
        songs = _setlist_songs(setlist_id, session)
        previous = (
            [(recommendation.artist, recommendation.title)]
            if recommendation.artist and recommendation.title
            else []
        )

    # The Gemini and Discogs calls can take seconds; don't hold a session.
    try:
        status, match = _pick_recommendation(songs, previous)
    except GeminiNotConfiguredError:
        logger.warning("GEMINI_API_KEY is not set; cannot recommend songs")
        status, match = RecommendationStatus.FAILED, None
    except Exception:
        logger.exception("Failed to pick a recommendation for setlist %s", setlist_id)
        status, match = RecommendationStatus.FAILED, None

    _save(setlist_id, request_id, status, match, engine)


def _setlist_songs(setlist_id: UUID, session: Session) -> list[tuple[str, str]]:
    statement = (
        select(Song.artist, Song.title)
        .join(SetlistEntry, SetlistEntry.song_id == Song.id)
        .where(SetlistEntry.setlist_id == setlist_id)
        .order_by(SetlistEntry.position)
    )
    return [(artist, title) for artist, title in session.exec(statement).all()]


def _pick_recommendation(
    songs: list[tuple[str, str]], previous: list[tuple[str, str]]
) -> tuple[RecommendationStatus, DiscogsSearchResult | None]:
    if not songs:
        return RecommendationStatus.NOT_FOUND, None

    taken = {_key(artist, title) for artist, title in songs + previous}
    for artist, title in suggest_songs(songs, exclude=previous):
        if _key(artist, title) in taken:
            continue
        match = find_track(artist, title)
        if match and _key(match.artist, match.title) not in taken:
            return RecommendationStatus.READY, match
    return RecommendationStatus.NOT_FOUND, None


def _key(artist: str, title: str) -> tuple[str, str]:
    return (" ".join(artist.casefold().split()), " ".join(title.casefold().split()))


def _save(
    setlist_id: UUID,
    request_id: UUID,
    status: RecommendationStatus,
    match: DiscogsSearchResult | None,
    engine: Engine,
) -> None:
    with Session(engine) as session:
        recommendation = session.get(SetlistRecommendation, setlist_id)
        # A newer request arrived while this one was talking to the APIs.
        if recommendation is None or recommendation.request_id != request_id:
            return

        recommendation.status = status
        recommendation.title = match.title if match else None
        recommendation.artist = match.artist if match else None
        recommendation.album = match.album if match else None
        recommendation.release_year = match.release_year if match else None
        recommendation.duration_ms = match.duration_ms if match else None
        recommendation.thumbnail = match.thumbnail if match else None
        recommendation.discogs_id = match.discogs_id if match else None
        recommendation.discogs_url = match.discogs_url if match else None
        session.add(recommendation)
        session.commit()
