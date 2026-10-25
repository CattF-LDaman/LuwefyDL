import shutil
from pathlib import Path

import pytest
from mutagen.mp3 import MP3

from music_importer.config import Config
from music_importer.library import LibraryManager
from music_importer.metadata import MetadataManager

FIXTURE_MP3 = Path(__file__).resolve().parent / "fixtures" / "silence.mp3"


def _place_track(library: Path, artist: str, album: str, name: str) -> Path:
    dest_dir = library / artist / album
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copy(FIXTURE_MP3, dest)
    return dest


@pytest.mark.asyncio
async def test_scan_finds_nested_tracks(isolated_env):
    lib = isolated_env["music"]
    _place_track(lib, "Band", "Album", "song.mp3")
    mgr = LibraryManager(Config())
    tracks = mgr.scan(str(lib))
    assert len(tracks) == 1
    assert tracks[0].artist == "Band"
    assert tracks[0].album == "Album"


@pytest.mark.asyncio
async def test_read_track_after_embed(isolated_env, sample_mp3_with_tags):
    lib = isolated_env["music"]
    track = _place_track(lib, "A", "B", "t.mp3")
    meta_mgr = MetadataManager(Config())
    await meta_mgr.embed_metadata(
        str(track),
        {
            "title": "Hello",
            "artist": "Artist One",
            "album": "Album One",
            "year": "2020",
            "genre": "Pop",
        },
    )
    mgr = LibraryManager(Config())
    record = mgr.read_track(str(track), str(lib))
    assert record.title == "Hello"
    assert record.artist == "Artist One"


@pytest.mark.asyncio
async def test_update_track_moves_file(isolated_env, sample_mp3_with_tags):
    lib = isolated_env["music"]
    track = _place_track(lib, "OldArtist", "OldAlbum", "OldTitle.mp3")
    await MetadataManager(Config()).embed_metadata(
        str(track),
        {
            "title": "OldTitle",
            "artist": "OldArtist",
            "album": "OldAlbum",
        },
    )
    mgr = LibraryManager(Config())
    new_path = await mgr.update_track(
        str(track),
        str(lib),
        {
            "title": "NewTitle",
            "artist": "NewArtist",
            "album": "NewAlbum",
            "year": "",
            "genre": "",
        },
    )
    assert Path(new_path).is_file()
    assert "NewArtist" in new_path and "NewAlbum" in new_path
    assert not track.exists()
    audio = MP3(new_path)
    assert str(audio.tags["TIT2"]) == "NewTitle"


def test_delete_track_and_prune_dirs(isolated_env):
    lib = isolated_env["music"]
    track = _place_track(lib, "DelArtist", "DelAlbum", "gone.mp3")
    mgr = LibraryManager(Config())
    mgr.delete_track(str(track), str(lib))
    assert not track.exists()
    assert not (lib / "DelArtist" / "DelAlbum").exists()


def test_delete_rejects_outside_library(isolated_env, tmp_path):
    lib = isolated_env["music"]
    outside = tmp_path / "outside.mp3"
    shutil.copy(FIXTURE_MP3, outside)
    mgr = LibraryManager(Config())
    with pytest.raises(Exception, match="outside the music library"):
        mgr.delete_track(str(outside), str(lib))


def test_scan_skips_non_audio(isolated_env):
    lib = isolated_env["music"]
    (lib / "notes.txt").write_text("nope")
    _place_track(lib, "A", "B", "ok.mp3")
    assert len(LibraryManager(Config()).scan(str(lib))) == 1


def test_read_metadata_from_mp3(isolated_env, sample_mp3_with_tags):
    meta = MetadataManager(Config())
    meta.read_metadata(str(sample_mp3_with_tags))
    # fixture may have empty tags; title falls back to stem
    assert meta.read_metadata(str(sample_mp3_with_tags))["title"]
