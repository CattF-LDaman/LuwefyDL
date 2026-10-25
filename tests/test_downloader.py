import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from music_importer.config import Config
from music_importer.downloader import YouTubeDownloader


def _mock_process(stdout: bytes, stderr: bytes = b"", returncode: int = 0):
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


@pytest.mark.asyncio
async def test_search_youtube_parses_lines(isolated_env):
    line = json.dumps(
        {
            "title": "Song",
            "id": "abc123",
            "duration": "3:00",
            "url": "https://www.youtube.com/watch?v=abc123",
        }
    )
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(f"{line}\n".encode()),
    ):
        dl = YouTubeDownloader(Config())
        results = await dl.search_youtube("query")
    assert len(results) == 1
    assert results[0]["title"] == "Song"
    assert "abc123" in results[0]["thumbnail"]


@pytest.mark.asyncio
async def test_search_youtube_subprocess_error(isolated_env):
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(b"", b"yt-dlp failed", returncode=1),
    ):
        dl = YouTubeDownloader(Config())
        with pytest.raises(Exception, match="yt-dlp search failed"):
            await dl.search_youtube("query")


@pytest.mark.asyncio
async def test_get_video_info(isolated_env):
    payload = {
        "title": "Video",
        "id": "vid1",
        "duration": "4:20",
        "url": "https://www.youtube.com/watch?v=vid1",
    }
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(json.dumps(payload).encode()),
    ):
        dl = YouTubeDownloader(Config())
        info = await dl.get_video_info("https://youtube.com/watch?v=vid1")
    assert info["title"] == "Video"
    assert info["id"] == "vid1"


@pytest.mark.asyncio
async def test_download_audio_finds_newest_file(isolated_env):
    temp = Path(isolated_env["temp"])
    expected = temp / "downloaded.mp3"
    expected.write_bytes(b"mp3")

    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(b"", b""),
    ):
        dl = YouTubeDownloader(Config())
        path = await dl.download_audio("https://youtube.com/watch?v=x")
    assert path == str(expected)


@pytest.mark.asyncio
async def test_download_audio_parses_destination_line(isolated_env):
    temp = Path(isolated_env["temp"])
    dest = temp / "song.mp3"
    dest.write_bytes(b"mp3")
    stdout = f"[ExtractAudio] Destination: {dest}\n".encode()

    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(stdout, b""),
    ):
        dl = YouTubeDownloader(Config())
        path = await dl.download_audio("https://youtube.com/watch?v=x")
    assert path == str(dest)


@pytest.mark.asyncio
async def test_get_video_info_error(isolated_env):
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(b"", b"fail", returncode=1),
    ):
        dl = YouTubeDownloader(Config())
        with pytest.raises(Exception, match="yt-dlp info failed"):
            await dl.get_video_info("https://youtube.com/watch?v=x")


@pytest.mark.asyncio
async def test_download_audio_already_downloaded_line(isolated_env):
    temp = Path(isolated_env["temp"])
    dest = temp / "cached.mp3"
    dest.write_bytes(b"mp3")
    stdout = f"[download] '{dest}' has already been downloaded\n".encode()
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(stdout, b""),
    ):
        dl = YouTubeDownloader(Config())
        path = await dl.download_audio("https://youtube.com/watch?v=x")
    assert path == str(dest)


@pytest.mark.asyncio
async def test_download_audio_falls_back_to_m4a(isolated_env):
    temp = Path(isolated_env["temp"])
    m4a = temp / "track.m4a"
    m4a.write_bytes(b"m4a")
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(b"", b""),
    ):
        dl = YouTubeDownloader(Config())
        path = await dl.download_audio("https://youtube.com/watch?v=x")
    assert path == str(m4a)


@pytest.mark.asyncio
async def test_ytdlp_not_found(isolated_env):
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError,
    ):
        dl = YouTubeDownloader(Config())
        with pytest.raises(Exception, match="yt-dlp not found"):
            await dl.search_youtube("q")


@pytest.mark.asyncio
async def test_search_skips_invalid_json_lines(isolated_env):
    line = json.dumps({"title": "Ok", "id": "1", "duration": "1:00", "url": "http://x"})
    stdout = f"not-json\n{line}\n".encode()
    with patch(
        "music_importer.downloader.asyncio.create_subprocess_exec",
        return_value=_mock_process(stdout, b""),
    ):
        dl = YouTubeDownloader(Config())
        results = await dl.search_youtube("q")
    assert len(results) == 1
