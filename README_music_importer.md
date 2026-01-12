# YouTube to Navidrome Music Importer

A web application built with NiceGUI that allows you to easily add music files to your Navidrome library from YouTube. Features automatic metadata fetching from iTunes API, manual editing capabilities, and proper file organization.

## Features

- **YouTube Search**: Search for music directly from YouTube
- **Direct Link Support**: Paste YouTube URLs directly
- **iTunes API Integration**: Automatically fetch metadata (title, artist, album, year, genre) and cover art
- **Manual Metadata Editing**: Edit all metadata fields manually
- **Manual iTunes Search**: Search iTunes API manually for better results
- **Cover Art**: Download and embed high-quality cover art
- **Organized Library**: Files are organized by Artist/Album structure
- **Metadata Embedding**: Properly embeds metadata into MP3 and M4A files

## Requirements

- Python 3.8+
- yt-dlp (installed via pip)
- Windows (development) or Linux (production server)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set the music library path (optional):
   - On Linux server: The default path is `/mnt/TOPHDD/music_library`
   - On Windows: Set the `MUSIC_LIBRARY_PATH` environment variable
   - Example: `set MUSIC_LIBRARY_PATH=C:\Music` (Windows) or `export MUSIC_LIBRARY_PATH=/path/to/music` (Linux)

## Usage

1. Run the application:
```bash
python -m music_importer.main
```

2. Open your browser to `http://localhost:8080`

3. Use the interface to:
   - Search YouTube for music
   - Or paste a YouTube URL directly
   - Review and edit metadata
   - Search iTunes API for better metadata
   - Download and add to your Navidrome library

## File Organization

Files are saved in the following structure:
```
music_library/
  Artist Name/
    Album Name/
      Song Title.mp3
```

## Configuration

The music library path can be configured via:
- Environment variable: `MUSIC_LIBRARY_PATH`
- Default: `/mnt/TOPHDD/music_library` (Linux) or `C:/Music` (Windows)

## Notes

- Temporary files are stored in a `temp/` directory in the project root
- The app supports MP3 and M4A formats
- Cover art is automatically downloaded from iTunes when available
- All metadata can be manually edited before saving

