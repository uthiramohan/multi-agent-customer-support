import json

import pytest

from src.tools.music_tools import (
    MUSIC_TOOLS, get_albums_by_artist, get_song_by_title, get_songs_by_genre,
    get_track_details, get_tracks_by_artist,
)


# ---- get_albums_by_artist ---------------------------------------------------
def test_albums_by_artist_found(call):
    _, data = call(get_albums_by_artist, artist="AC/DC")
    assert data["status"] == "ok" and data["total_count"] >= 1
    assert all(r["ArtistName"] == "AC/DC" for r in data["results"])


def test_albums_by_artist_fuzzy(call):
    _, data = call(get_albums_by_artist, artist="zeppelin")
    assert any(r["ArtistName"] == "Led Zeppelin" for r in data["results"])


def test_albums_by_artist_not_found(call):
    _, data = call(get_albums_by_artist, artist="NonexistentArtistXYZ")
    assert data["status"] == "not_found"
    assert "NonexistentArtistXYZ" in data["message"]


def test_albums_by_artist_wildcard_is_literal(call):
    _, data = call(get_albums_by_artist, artist="%")
    assert data["status"] == "not_found"


# ---- get_tracks_by_artist ---------------------------------------------------
def test_tracks_by_artist_count_and_sample(call):
    _, data = call(get_tracks_by_artist, artist="Iron Maiden")
    assert data["total_count"] > 20
    assert data["returned_count"] == 20 and data["truncated"] is True


def test_tracks_by_artist_not_found(call):
    _, data = call(get_tracks_by_artist, artist="NoSuchBand123")
    assert data["status"] == "not_found"


# ---- get_songs_by_genre -----------------------------------------------------
def test_songs_by_genre_is_diverse(call):
    _, data = call(get_songs_by_genre, genre="Rock")
    artists = [r["ArtistName"] for r in data["results"]]
    assert len(artists) == 10
    assert len(set(artists)) == len(artists)  # one track per artist
    assert data["total_count"] > data["returned_count"]


def test_songs_by_genre_is_deterministic():
    first = get_songs_by_genre.invoke({"genre": "Rock"})
    assert all(get_songs_by_genre.invoke({"genre": "Rock"}) == first for _ in range(5))


def test_songs_by_genre_not_found(call):
    _, data = call(get_songs_by_genre, genre="Polka-Dubstep")
    assert data["status"] == "not_found"


def test_songs_by_genre_empty_input(call):
    _, data = call(get_songs_by_genre, genre="  ")
    assert data["status"] == "error"


# ---- get_song_by_title ------------------------------------------------------
def test_song_by_title_fuzzy(call):
    _, data = call(get_song_by_title, title="balls to the")
    assert any(r["SongName"] == "Balls to the Wall" for r in data["results"])


def test_song_by_title_limit(call):
    _, data = call(get_song_by_title, title="love")
    assert data["returned_count"] <= 10 and data["total_count"] >= data["returned_count"]


def test_song_by_title_not_found(call):
    _, data = call(get_song_by_title, title="zzqqxx-no-song")
    assert data["status"] == "not_found"


# ---- get_track_details ------------------------------------------------------
def test_track_details_found(call):
    _, data = call(get_track_details, track_id="1")
    track = data["results"][0]
    assert track["TrackId"] == 1 and track["ArtistName"] == "AC/DC"
    assert {"Genre", "MediaType", "Milliseconds", "UnitPrice"} <= track.keys()


def test_track_details_not_found(call):
    _, data = call(get_track_details, track_id="999999")
    assert data["status"] == "not_found"


@pytest.mark.parametrize("bad", ["abc", "-1", "0", "1 OR 1=1"])
def test_track_details_invalid_id(call, bad):
    _, data = call(get_track_details, track_id=bad)
    assert data["status"] == "error"


# ---- JSON validity across all music tools ----------------------------------
@pytest.mark.parametrize("tool, args", [
    (get_albums_by_artist, {"artist": "Queen"}),
    (get_albums_by_artist, {"artist": "zzz"}),
    (get_tracks_by_artist, {"artist": "Queen"}),
    (get_songs_by_genre, {"genre": "Jazz"}),
    (get_song_by_title, {"title": "Yesterday"}),
    (get_track_details, {"track_id": "abc"}),
])
def test_music_outputs_are_valid_json(tool, args):
    assert isinstance(json.loads(tool.invoke(args)), dict)


def test_five_music_tools_registered():
    assert len(MUSIC_TOOLS) == 5
