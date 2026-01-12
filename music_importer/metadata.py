"""
Metadata management using iTunes API and mutagen for embedding
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover
import os


class MetadataManager:
    """Handle metadata fetching from iTunes and embedding into audio files"""
    
    def __init__(self):
        self.itunes_base_url = "https://itunes.apple.com/search"
        self.temp_dir = Path(__file__).parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
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
                "limit": limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.itunes_base_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"iTunes API returned status {response.status}")
                    
                    data = await response.json()
                    return data.get("results", [])
                    
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
                    
                    audio_file['covr'] = [MP4Cover(cover_data)]
                
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
            library = Path(library_path)
            
            # Organize by artist/album structure
            artist = metadata.get('artist', 'Unknown Artist')
            album = metadata.get('album', 'Unknown Album')
            
            # Clean names for filesystem
            artist = self._clean_filename(artist)
            album = self._clean_filename(album)
            
            # Create directory structure: library/Artist/Album/
            target_dir = library / artist / album
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine filename
            title = metadata.get('title', 'Unknown Title')
            title = self._clean_filename(title)
            
            # Get file extension from source
            source_ext = Path(audio_path).suffix
            filename = f"{title}{source_ext}"
            
            # Handle duplicates
            target_path = target_dir / filename
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{title} ({counter}){source_ext}"
                counter += 1
            
            # Copy file to library
            import shutil
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

