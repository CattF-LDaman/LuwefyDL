"""
Metadata management using iTunes API and mutagen for embedding
"""

import asyncio
import aiohttp
import aiofiles
import json
from pathlib import Path
from typing import Dict, List, Optional
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover
import os

from music_importer import __version__
from music_importer.config import Config


def _parse_itunes_response(text: str) -> list:
    """Parse JSON from iTunes search API, including JSONP-style wrappers."""
    try:
        data = json.loads(text)
        return data.get("results", [])
    except json.JSONDecodeError:
        stripped = text.strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(stripped[start : end + 1])
            return data.get("results", [])
        raise ValueError(f"Invalid JSON response from iTunes API: {text[:200]}")


class MetadataManager:
    """Handle metadata fetching from iTunes and embedding into audio files"""

    def __init__(self, config: Optional[Config] = None):
        self.itunes_base_url = "https://itunes.apple.com/search"
        cfg = config or Config()
        self.temp_dir = Path(cfg.get_temp_dir())
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = f"LuwefyDL/{__version__}"
    
    async def search_itunes(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search iTunes API for music metadata
        
        Args:
            query: Search query (song name, artist, etc.)
            limit: Maximum number of results
            
        Returns:
            List of iTunes search results
        """
        try:
            params = {
                "term": query,
                "media": "music",
                "entity": "song",
                "limit": limit
            }
            
            # Set headers to request JSON response
            headers = {
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.itunes_base_url, 
                    params=params, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"iTunes API returned status {response.status}")
                    
                    text = await response.text()
                    try:
                        return _parse_itunes_response(text)
                    except ValueError as e:
                        raise Exception(str(e)) from e
                    
        except asyncio.TimeoutError:
            raise Exception("iTunes API request timed out")
        except aiohttp.ClientError as e:
            raise Exception(f"iTunes API connection error: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"iTunes API returned invalid JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"iTunes search failed: {str(e)}")
    
    async def download_cover_art(self, url: str) -> Optional[str]:
        """
        Download cover art image
        
        Args:
            url: URL of the cover art image
            
        Returns:
            Path to downloaded cover art file, or None if download failed
        """
        try:
            # Determine file extension from URL
            ext = "jpg"
            if ".png" in url.lower():
                ext = "png"
            elif ".gif" in url.lower():
                ext = "gif"
            
            output_path = self.temp_dir / f"cover_{os.urandom(4).hex()}.{ext}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            
            return str(output_path)
            
        except Exception as e:
            print(f"Failed to download cover art: {str(e)}")
            return None
    
    async def embed_metadata(
        self,
        audio_path: str,
        metadata: Dict,
        cover_art_path: Optional[str] = None
    ) -> str:
        """
        Embed metadata into audio file
        
        Args:
            audio_path: Path to audio file
            metadata: Dictionary with metadata (title, artist, album, year, genre)
            cover_art_path: Optional path to cover art image
            
        Returns:
            Path to the file with embedded metadata (may be same as input)
        """
        try:
            audio_file = mutagen.File(audio_path)
            
            if audio_file is None:
                raise Exception(f"Could not load audio file: {audio_path}")
            
            # Handle MP3 files
            if isinstance(audio_file, MP3):
                if not audio_file.tags:
                    audio_file.add_tags()
                
                tags = audio_file.tags
                
                if metadata.get('title'):
                    tags['TIT2'] = TIT2(encoding=3, text=metadata['title'])
                if metadata.get('artist'):
                    tags['TPE1'] = TPE1(encoding=3, text=metadata['artist'])
                if metadata.get('album'):
                    tags['TALB'] = TALB(encoding=3, text=metadata['album'])
                if metadata.get('year'):
                    tags['TDRC'] = TDRC(encoding=3, text=metadata['year'])
                if metadata.get('genre'):
                    tags['TCON'] = TCON(encoding=3, text=metadata['genre'])
                
                # Add cover art
                if cover_art_path and os.path.exists(cover_art_path):
                    with open(cover_art_path, 'rb') as f:
                        cover_data = f.read()
                    
                    # Determine MIME type
                    mime_type = "image/jpeg"
                    if cover_art_path.lower().endswith('.png'):
                        mime_type = "image/png"
                    elif cover_art_path.lower().endswith('.gif'):
                        mime_type = "image/gif"
                    
                    tags['APIC'] = APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=cover_data
                    )
                
                audio_file.save()
            
            # Handle MP4/M4A files
            elif isinstance(audio_file, MP4):
                if metadata.get('title'):
                    audio_file['\xa9nam'] = [metadata['title']]
                if metadata.get('artist'):
                    audio_file['\xa9ART'] = [metadata['artist']]
                if metadata.get('album'):
                    audio_file['\xa9alb'] = [metadata['album']]
                if metadata.get('year'):
                    audio_file['\xa9day'] = [metadata['year']]
                if metadata.get('genre'):
                    audio_file['\xa9gen'] = [metadata['genre']]
                
                # Add cover art
                if cover_art_path and os.path.exists(cover_art_path):
                    with open(cover_art_path, 'rb') as f:
                        cover_data = f.read()
                    
                    # Determine format from file extension
                    cover_format = MP4Cover.FORMAT_JPEG  # Default to JPEG
                    if cover_art_path.lower().endswith('.png'):
                        cover_format = MP4Cover.FORMAT_PNG
                    elif cover_art_path.lower().endswith('.gif'):
                        cover_format = MP4Cover.FORMAT_GIF
                    
                    audio_file['covr'] = [MP4Cover(cover_data, cover_format)]
                
                audio_file.save()
            
            else:
                # Try generic mutagen approach
                if metadata.get('title'):
                    audio_file['title'] = metadata['title']
                if metadata.get('artist'):
                    audio_file['artist'] = metadata['artist']
                if metadata.get('album'):
                    audio_file['album'] = metadata['album']
                if metadata.get('year'):
                    audio_file['date'] = metadata['year']
                if metadata.get('genre'):
                    audio_file['genre'] = metadata['genre']
                
                audio_file.save()
            
            return audio_path
            
        except Exception as e:
            raise Exception(f"Failed to embed metadata: {str(e)}")

    def read_metadata(self, audio_path: str) -> Dict[str, str]:
        """Read embedded metadata from an audio file."""
        path = Path(audio_path)
        empty = {
            "title": "",
            "artist": "",
            "album": "",
            "year": "",
            "genre": "",
        }
        if not path.is_file():
            raise Exception(f"Audio file not found: {audio_path}")

        audio_file = mutagen.File(audio_path)
        if audio_file is None:
            raise Exception(f"Could not load audio file: {audio_path}")

        meta = dict(empty)
        if isinstance(audio_file, MP3) and audio_file.tags:
            tags = audio_file.tags
            if "TIT2" in tags:
                meta["title"] = str(tags["TIT2"])
            if "TPE1" in tags:
                meta["artist"] = str(tags["TPE1"])
            if "TALB" in tags:
                meta["album"] = str(tags["TALB"])
            if "TDRC" in tags:
                meta["year"] = str(tags["TDRC"])[:4]
            if "TCON" in tags:
                meta["genre"] = str(tags["TCON"])
        elif isinstance(audio_file, MP4):
            if "\xa9nam" in audio_file:
                meta["title"] = audio_file["\xa9nam"][0]
            if "\xa9ART" in audio_file:
                meta["artist"] = audio_file["\xa9ART"][0]
            if "\xa9alb" in audio_file:
                meta["album"] = audio_file["\xa9alb"][0]
            if "\xa9day" in audio_file:
                meta["year"] = str(audio_file["\xa9day"][0])[:4]
            if "\xa9gen" in audio_file:
                meta["genre"] = audio_file["\xa9gen"][0]
        else:
            for key, tag_key in (
                ("title", "title"),
                ("artist", "artist"),
                ("album", "album"),
                ("year", "date"),
                ("genre", "genre"),
            ):
                if tag_key in audio_file:
                    val = audio_file[tag_key]
                    meta[key] = val[0] if isinstance(val, list) else str(val)
                    if key == "year" and meta[key]:
                        meta[key] = meta[key][:4]

        if not meta["title"]:
            meta["title"] = path.stem
        return meta

    def target_path_for_metadata(
        self,
        library: Path,
        metadata: Dict,
        ext: str,
        exclude_path: Optional[Path] = None,
    ) -> Path:
        """Compute library path for metadata (Artist/Album/Title.ext)."""
        artist = self._clean_filename(metadata.get("artist") or "Unknown Artist")
        album = self._clean_filename(metadata.get("album") or "Unknown Album")
        title = self._clean_filename(metadata.get("title") or "Unknown Title")

        target_dir = library / artist / album
        target_dir.mkdir(parents=True, exist_ok=True)

        if not ext.startswith("."):
            ext = f".{ext}"

        target_path = target_dir / f"{title}{ext}"
        counter = 1
        exclude_resolved = exclude_path.resolve() if exclude_path else None
        while target_path.exists() and target_path.resolve() != exclude_resolved:
            target_path = target_dir / f"{title} ({counter}){ext}"
            counter += 1
        return target_path
    
    async def save_to_library(
        self,
        audio_path: str,
        library_path: str,
        metadata: Dict
    ) -> str:
        """
        Save audio file to music library with proper organization
        
        Args:
            audio_path: Path to audio file
            library_path: Root path of music library
            metadata: Metadata dictionary
            
        Returns:
            Final path where file was saved
        """
        try:
            import shutil

            library = Path(library_path)
            source_ext = Path(audio_path).suffix
            target_path = self.target_path_for_metadata(library, metadata, source_ext)
            shutil.copy2(audio_path, target_path)
            return str(target_path)
            
        except Exception as e:
            raise Exception(f"Failed to save to library: {str(e)}")
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename

