import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from music_importer.config import Config
from music_importer.metadata import MetadataManager, _parse_itunes_response

FIXTURE_M4A = Path(__file__).resolve().parent / "fixtures" / "silence.m4a"


def test_parse_itunes_response_plain_json():
    payload = {"results": [{"trackName": "Song"}]}
    assert _parse_itunes_response(json.dumps(payload)) == payload["results"]


def test_parse_itunes_response_jsonp_wrapper():
    inner = {"results": [{"trackName": "Wrapped"}]}
    text = f"callback({json.dumps(inner)})"
    assert _parse_itunes_response(text) == inner["results"]


def test_parse_itunes_response_invalid():
    with pytest.raises(ValueError, match="Invalid JSON"):
        _parse_itunes_response("not json")


def test_clean_filename():
    mgr = MetadataManager(Config())
    assert mgr._clean_filename("Artist: Name<>") == "Artist_ Name__"
    long_name = "a" * 250
    assert len(mgr._clean_filename(long_name)) == 200


def _session_mock(response):
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            return response

    return FakeSession


@pytest.mark.asyncio
async def test_search_itunes(isolated_env):
    mgr = MetadataManager(Config())

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def text(self):
            return json.dumps(
                {"results": [{"trackName": "Test Track", "artistName": "Artist"}]}
            )

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=_session_mock(FakeResponse())(),
    ):
        results = await mgr.search_itunes("test query")
    assert len(results) == 1
    assert results[0]["trackName"] == "Test Track"


@pytest.mark.asyncio
async def test_search_itunes_http_error(isolated_env):
    mgr = MetadataManager(Config())

    class FakeResponse:
        status = 500

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def text(self):
            return ""

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=_session_mock(FakeResponse())(),
    ):
        with pytest.raises(Exception, match="status 500"):
            await mgr.search_itunes("fail")


@pytest.mark.asyncio
async def test_embed_metadata_mp3_with_cover(isolated_env, sample_mp3_with_tags):
    mgr = MetadataManager(Config())
    cover = isolated_env["temp"] / "cover.jpg"
    cover.write_bytes(b"jpeg-bytes")
    metadata = {
        "title": "T",
        "artist": "A",
        "album": "B",
        "year": "2020",
        "genre": "Pop",
    }
    result_path = await mgr.embed_metadata(
        str(sample_mp3_with_tags), metadata, str(cover)
    )
    audio = MP3(result_path)
    assert str(audio.tags["TIT2"]) == "T"
    assert any(key.startswith("APIC") for key in audio.tags)


@pytest.mark.asyncio
async def test_embed_metadata_mp3(isolated_env, sample_mp3_with_tags):
    mgr = MetadataManager(Config())
    metadata = {
        "title": "My Title",
        "artist": "My Artist",
        "album": "My Album",
        "year": "2024",
        "genre": "Rock",
    }
    result_path = await mgr.embed_metadata(str(sample_mp3_with_tags), metadata)
    audio = MP3(result_path)
    assert str(audio.tags["TIT2"]) == "My Title"
    assert str(audio.tags["TPE1"]) == "My Artist"


@pytest.mark.asyncio
async def test_embed_metadata_invalid_file(isolated_env):
    mgr = MetadataManager(Config())
    bad = isolated_env["temp"] / "bad.txt"
    bad.write_text("not audio")
    with pytest.raises(Exception, match="Could not load audio file"):
        await mgr.embed_metadata(str(bad), {"title": "x"})


@pytest.mark.asyncio
async def test_save_to_library_and_duplicate(isolated_env, sample_mp3):
    mgr = MetadataManager(Config())
    library = isolated_env["music"]
    metadata = {
        "title": "Track One",
        "artist": "Band",
        "album": "Album",
    }
    dest = await mgr.save_to_library(str(sample_mp3), str(library), metadata)
    assert Path(dest).is_file()
    assert "Band" in dest and "Album" in dest

    dest2 = await mgr.save_to_library(str(sample_mp3), str(library), metadata)
    assert dest2 != dest
    assert "(1)" in dest2


@pytest.mark.asyncio
async def test_download_cover_art(isolated_env):
    mgr = MetadataManager(Config())

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        @property
        def content(self):
            class Content:
                async def iter_chunked(self, n):
                    yield b"fake-image-bytes"

            return Content()

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=_session_mock(FakeResponse())(),
    ):
        path = await mgr.download_cover_art("https://example.com/cover.png")
    assert path is not None
    assert path.endswith(".png")
    assert Path(path).read_bytes() == b"fake-image-bytes"


@pytest.mark.asyncio
async def test_embed_metadata_m4a(isolated_env):
    mgr = MetadataManager(Config())
    path = isolated_env["temp"] / "track.m4a"
    shutil.copy(FIXTURE_M4A, path)
    metadata = {
        "title": "M4A Title",
        "artist": "Artist",
        "album": "Album",
        "year": "2021",
        "genre": "Jazz",
    }
    result = await mgr.embed_metadata(str(path), metadata)
    audio = MP4(result)
    assert audio["\xa9nam"] == ["M4A Title"]


@pytest.mark.asyncio
async def test_search_itunes_invalid_json_body(isolated_env):
    mgr = MetadataManager(Config())

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def text(self):
            return "broken"

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=_session_mock(FakeResponse())(),
    ):
        with pytest.raises(Exception, match="Invalid JSON"):
            await mgr.search_itunes("x")


@pytest.mark.asyncio
async def test_search_itunes_client_error(isolated_env):
    mgr = MetadataManager(Config())

    class BrokenSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            raise aiohttp.ClientError("offline")

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=BrokenSession(),
    ):
        with pytest.raises(Exception, match="connection error"):
            await mgr.search_itunes("x")


@pytest.mark.asyncio
async def test_search_itunes_timeout(isolated_env):
    mgr = MetadataManager(Config())

    class SlowSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            raise asyncio.TimeoutError

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=SlowSession(),
    ):
        with pytest.raises(Exception, match="timed out"):
            await mgr.search_itunes("x")


@pytest.mark.asyncio
async def test_save_to_library_missing_source(isolated_env):
    mgr = MetadataManager(Config())
    with pytest.raises(Exception, match="Failed to save to library"):
        await mgr.save_to_library(
            str(isolated_env["temp"] / "missing.mp3"),
            str(isolated_env["music"]),
            {"title": "T", "artist": "A", "album": "B"},
        )


@pytest.mark.asyncio
async def test_download_cover_art_non_200(isolated_env):
    mgr = MetadataManager(Config())

    class FakeResponse:
        status = 404

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    with patch(
        "music_importer.metadata.aiohttp.ClientSession",
        return_value=_session_mock(FakeResponse())(),
    ):
        assert await mgr.download_cover_art("https://example.com/missing.jpg") is None
