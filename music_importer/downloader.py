"""
YouTube downloader using yt-dlp
"""

import asyncio
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Optional


class YouTubeDownloader:
    """Handle YouTube video downloading and searching"""
    
    def __init__(self):
        self.temp_dir = Path(__file__).parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def search_youtube(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search YouTube for videos
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of video dictionaries with title, url, duration, thumbnail
        """
        try:
            # Use yt-dlp to search YouTube
            cmd = [
                "yt-dlp",
                "--flat-playlist",
                "--print", "{\"title\": \"%(title)s\", \"id\": \"%(id)s\", \"duration\": \"%(duration_string)s\", \"url\": \"%(webpage_url)s\"}",
                f"ytsearch{max_results}:{query}"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"yt-dlp search failed: {error_msg}")
            
            results = []
            for line in stdout.decode().strip().split('\n'):
                if line.strip():
                    try:
                        video_data = json.loads(line)
                        # Get thumbnail URL
                        video_id = video_data.get('id', '')
                        thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        
                        results.append({
                            'title': video_data.get('title', 'Unknown'),
                            'url': video_data.get('url', ''),
                            'duration': video_data.get('duration', 'Unknown'),
                            'thumbnail': thumbnail,
                            'id': video_id
                        })
                    except json.JSONDecodeError:
                        continue
            
            return results
            
        except FileNotFoundError:
            raise Exception("yt-dlp not found. Please install it: pip install yt-dlp")
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    async def get_video_info(self, url: str) -> Dict:
        """
        Get information about a YouTube video
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video information
        """
        try:
            cmd = [
                "yt-dlp",
                "--print", "{\"title\": \"%(title)s\", \"id\": \"%(id)s\", \"duration\": \"%(duration_string)s\", \"url\": \"%(webpage_url)s\"}",
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"yt-dlp info failed: {error_msg}")
            
            video_data = json.loads(stdout.decode().strip())
            video_id = video_data.get('id', '')
            thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            
            return {
                'title': video_data.get('title', 'Unknown'),
                'url': video_data.get('url', url),
                'duration': video_data.get('duration', 'Unknown'),
                'thumbnail': thumbnail,
                'id': video_id
            }
            
        except FileNotFoundError:
            raise Exception("yt-dlp not found. Please install it: pip install yt-dlp")
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    async def download_audio(self, url: str, output_format: str = "mp3") -> str:
        """
        Download audio from YouTube video
        
        Args:
            url: YouTube video URL
            output_format: Output format (mp3, m4a, etc.)
            
        Returns:
            Path to downloaded audio file
        """
        try:
            output_template = str(self.temp_dir / "%(title)s.%(ext)s")
            
            # Clean filename for filesystem
            output_template = output_template.replace(" ", "_")
            
            cmd = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", output_format,
                "--audio-quality", "0",  # Best quality
                "-o", output_template,
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Download failed: {error_msg}")
            
            # Find the downloaded file
            # yt-dlp outputs the filename, but we need to find it
            output_text = stdout.decode()
            error_text = stderr.decode()
            
            downloaded_file = None
            
            # Try to extract filename from output
            for line in output_text.split('\n'):
                if '[ExtractAudio]' in line and 'Destination:' in line:
                    parts = line.split('Destination:')
                    if len(parts) >= 2:
                        downloaded_file = parts[1].strip()
                        break
                elif '[download]' in line and 'has already been downloaded' in line:
                    # Extract filename from quoted string
                    import re
                    match = re.search(r"'([^']+)'", line)
                    if match:
                        downloaded_file = match.group(1)
                        break
            
            # If we can't find it from output, search temp directory for most recent file
            if not downloaded_file or not os.path.exists(downloaded_file):
                # Get the most recently modified file in temp dir matching the format
                files = list(self.temp_dir.glob(f"*.{output_format}"))
                if files:
                    downloaded_file = str(max(files, key=os.path.getmtime))
                else:
                    # Try any audio format
                    for ext in ['mp3', 'm4a', 'opus', 'ogg', 'webm']:
                        files = list(self.temp_dir.glob(f"*.{ext}"))
                        if files:
                            downloaded_file = str(max(files, key=os.path.getmtime))
                            break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                # Last resort: list all files and get the newest
                all_files = [f for f in self.temp_dir.iterdir() if f.is_file()]
                if all_files:
                    downloaded_file = str(max(all_files, key=os.path.getmtime))
                else:
                    raise Exception(f"Downloaded file not found. Output: {output_text[:500]}, Error: {error_text[:500]}")
            
            return downloaded_file
            
        except FileNotFoundError:
            raise Exception("yt-dlp not found. Please install it: pip install yt-dlp")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

