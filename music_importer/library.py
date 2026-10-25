"""
Browse and manage tracks on disk under the configured music library.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from music_importer.config import Config
from music_importer.metadata import MetadataManager

AUDIO_EXTENSIONS = {".mp3", ".m4a"}


@dataclass
class TrackRecord:
    path: str
    title: str
    artist: str
    album: str
    year: str
    genre: str


class LibraryManager:
    """Scan, read, update, and delete library tracks."""

    def __init__(
        self,
        config: Optional[Config] = None,
        metadata_manager: Optional[MetadataManager] = None,
    ):
        self.config = config or Config()
        self.metadata = metadata_manager or MetadataManager(self.config)

    def scan(self, library_root: str) -> List[TrackRecord]:
        root = Path(library_root).resolve()
        if not root.is_dir():
            return []

        records: List[TrackRecord] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            try:
                meta = self.metadata.read_metadata(str(path))
            except Exception:
                meta = {
                    "title": path.stem,
                    "artist": "",
                    "album": "",
                    "year": "",
                    "genre": "",
                }
            if not meta.get("artist") and path.parent.parent != root:
                meta["artist"] = path.parent.parent.name
            if not meta.get("album") and path.parent != root:
                meta["album"] = path.parent.name

            records.append(
                TrackRecord(
                    path=str(path.resolve()),
                    title=meta.get("title", path.stem),
                    artist=meta.get("artist", ""),
                    album=meta.get("album", ""),
                    year=meta.get("year", ""),
                    genre=meta.get("genre", ""),
                )
            )

        records.sort(key=lambda t: (t.artist.lower(), t.album.lower(), t.title.lower()))
        return records

    def read_track(self, path: str, library_root: str) -> TrackRecord:
        resolved = self._resolve_under_root(path, library_root)
        meta = self.metadata.read_metadata(str(resolved))
        return TrackRecord(
            path=str(resolved),
            title=meta.get("title", resolved.stem),
            artist=meta.get("artist", ""),
            album=meta.get("album", ""),
            year=meta.get("year", ""),
            genre=meta.get("genre", ""),
        )

    async def update_track(
        self,
        path: str,
        library_root: str,
        metadata: Dict,
        cover_art_path: Optional[str] = None,
    ) -> str:
        source = self._resolve_under_root(path, library_root)
        library = Path(library_root).resolve()

        await self.metadata.embed_metadata(
            str(source), metadata, cover_art_path
        )

        target = self.metadata.target_path_for_metadata(
            library,
            metadata,
            source.suffix,
            exclude_path=source,
        )

        if target.resolve() != source.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            self._prune_empty_dirs(source.parent, library)

        return str(target.resolve())

    def delete_track(self, path: str, library_root: str) -> None:
        target = self._resolve_under_root(path, library_root)
        library = Path(library_root).resolve()
        parent = target.parent
        target.unlink()
        self._prune_empty_dirs(parent, library)

    def _resolve_under_root(self, path: str, library_root: str) -> Path:
        root = Path(library_root).resolve()
        resolved = Path(path).resolve()
        self._assert_under_root(resolved, root)
        if not resolved.is_file():
            raise Exception(f"Track not found: {path}")
        if resolved.suffix.lower() not in AUDIO_EXTENSIONS:
            raise Exception(f"Unsupported audio format: {resolved.suffix}")
        return resolved

    @staticmethod
    def _assert_under_root(resolved: Path, root: Path) -> None:
        try:
            resolved.relative_to(root)
        except ValueError as e:
            raise Exception("Path is outside the music library") from e

    @staticmethod
    def _prune_empty_dirs(start: Path, library_root: Path) -> None:
        current = start.resolve()
        root = library_root.resolve()
        while current != root and current.is_dir():
            if any(current.iterdir()):
                break
            parent = current.parent
            current.rmdir()
            current = parent
