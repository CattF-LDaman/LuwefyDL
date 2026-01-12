"""
YouTube to Navidrome Music Importer
A NiceGUI web app for easily adding music from YouTube to Navidrome library
"""

from nicegui import ui, app
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from music_importer.downloader import YouTubeDownloader
from music_importer.metadata import MetadataManager
from music_importer.config import Config

# Initialize configuration
config = Config()

# Set up static files (create directory if it doesn't exist)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.add_static_files("/static", str(static_dir))

@ui.page("/")
def main_page():
    """Main page with YouTube search and link input"""
    
    ui.colors(primary='#4CAF50', secondary='#333')
    ui.page_title("LuwefyDL")
    
    # Add custom styles for dark mode
    ui.add_head_html("""
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #e0e0e0;
        }
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        /* Ensure text is readable in dark mode */
        .text-gray-500 {
            color: #9e9e9e !important;
        }
        .text-gray-600 {
            color: #b0b0b0 !important;
        }
        /* Dark mode hover effects for cards */
        .dark-hover-card {
            transition: background-color 0.2s;
        }
        .dark-hover-card:hover {
            background-color: #2a2a2a !important;
        }
    </style>
    """)
    
    with ui.column().classes("main-container w-full gap-4"):
        ui.label("LuwefyDL").classes("text-3xl font-bold mb-4")
        
        with ui.card().classes("w-full p-4"):
            ui.label("Add Music from YouTube").classes("text-xl font-semibold mb-4")
            
            # Tabs for search vs link
            with ui.tabs().classes("w-full") as tabs:
                search_tab = ui.tab("Search")
                link_tab = ui.tab("Direct Link")
            
            with ui.tab_panels(tabs, value=search_tab).classes("w-full"):
                # Search tab
                with ui.tab_panel(search_tab):
                    search_input = ui.input(
                        label="Search YouTube",
                        placeholder="Enter song name, artist, etc."
                    ).classes("w-full mb-2")
                    
                    search_results_container = ui.column().classes("w-full mt-4")
                    
                    async def perform_search():
                        if not search_input.value:
                            ui.notify("Please enter a search term", type="warning")
                            return
                        
                        search_results_container.clear()
                        with search_results_container:
                            ui.spinner(size="lg")
                            ui.label("Searching...").classes("text-gray-500")
                        
                        try:
                            downloader = YouTubeDownloader()
                            results = await downloader.search_youtube(search_input.value)
                            
                            search_results_container.clear()
                            with search_results_container:
                                if not results:
                                    ui.label("No results found").classes("text-gray-500")
                                else:
                                    ui.label(f"Found {len(results)} results").classes("text-sm text-gray-400 mb-2")
                                    for result in results:
                                        with ui.card().classes("w-full p-3 mb-2"):
                                            with ui.row().classes("w-full items-center gap-4"):
                                                ui.label(result['title']).classes("flex-1 font-semibold")
                                                ui.label(result.get('duration', 'Unknown')).classes("text-sm text-gray-500")
                                                ui.button(
                                                    "Select",
                                                    icon="add",
                                                    on_click=lambda r=result: select_video(r)
                                                ).props("color=primary")
                        except Exception as e:
                            search_results_container.clear()
                            with search_results_container:
                                ui.label(f"Error: {str(e)}").classes("text-red-500")
                            ui.notify(f"Search failed: {str(e)}", type="negative")
                    
                    ui.button(
                        "Search",
                        icon="search",
                        on_click=perform_search
                    ).classes("w-full").props("color=primary")
                
                # Direct link tab
                with ui.tab_panel(link_tab):
                    link_input = ui.input(
                        label="YouTube URL",
                        placeholder="https://www.youtube.com/watch?v=..."
                    ).classes("w-full mb-2")
                    
                    async def process_link():
                        if not link_input.value:
                            ui.notify("Please enter a YouTube URL", type="warning")
                            return
                        
                        try:
                            downloader = YouTubeDownloader()
                            video_info = await downloader.get_video_info(link_input.value)
                            select_video(video_info)
                        except Exception as e:
                            ui.notify(f"Failed to get video info: {str(e)}", type="negative")
                    
                    ui.button(
                        "Process Link",
                        icon="link",
                        on_click=process_link
                    ).classes("w-full").props("color=primary")
        
        # Selected video and metadata section
        selected_video_container = ui.column().classes("w-full")
        
        def select_video(video_info):
            """Handle video selection and show metadata editor"""
            selected_video_container.clear()
            
            with selected_video_container:
                with ui.card().classes("w-full p-4"):
                    ui.label("Selected Video").classes("text-xl font-semibold mb-4")
                    
                    with ui.row().classes("w-full gap-4 mb-4"):
                        # Video info
                        with ui.column().classes("flex-1"):
                            ui.label("Title:").classes("font-semibold")
                            title_input = ui.input(value=video_info.get('title', '')).classes("w-full")
                            
                            ui.label("URL:").classes("font-semibold mt-2")
                            ui.label(video_info.get('url', '')).classes("text-sm text-gray-400")
                            
                            ui.label("Duration:").classes("font-semibold mt-2")
                            ui.label(video_info.get('duration', 'Unknown')).classes("text-sm text-gray-400")
                        
                        # Thumbnail preview
                        if 'thumbnail' in video_info:
                            ui.image(video_info['thumbnail']).classes("w-48 h-36 object-cover rounded")
                    
                    ui.separator()
                    
                    # Metadata section
                    ui.label("Metadata").classes("text-xl font-semibold mb-4 mt-4")
                    
                    metadata_manager = MetadataManager()
                    metadata_state = {
                        'title': video_info.get('title', ''),
                        'artist': '',
                        'album': '',
                        'year': '',
                        'genre': '',
                        'cover_art_url': '',
                        'itunes_results': []
                    }
                    
                    # Search iTunes button
                    async def search_itunes():
                        if not title_input.value:
                            ui.notify("Please enter a title first", type="warning")
                            return
                        
                        search_term = title_input.value
                        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
                            ui.label("Searching iTunes...").classes("text-lg font-semibold mb-4")
                            results_container = ui.column().classes("w-full")
                            
                            with results_container:
                                ui.spinner(size="lg")
                                ui.label("Searching...")
                            
                            try:
                                results = await metadata_manager.search_itunes(search_term)
                                metadata_state['itunes_results'] = results
                                
                                results_container.clear()
                                with results_container:
                                    if not results:
                                        ui.label("No results found").classes("text-gray-500")
                                    else:
                                        ui.label(f"Found {len(results)} results").classes("text-sm text-gray-400 mb-2")
                                        for idx, result in enumerate(results):
                                            with ui.card().classes("w-full p-3 mb-2 cursor-pointer dark-hover-card"):
                                                with ui.row().classes("w-full items-center gap-4"):
                                                    if result.get('artworkUrl100'):
                                                        ui.image(result['artworkUrl100']).classes("w-16 h-16 object-cover rounded")
                                                    with ui.column().classes("flex-1"):
                                                        ui.label(result.get('trackName', 'Unknown')).classes("font-semibold")
                                                        ui.label(f"{result.get('artistName', 'Unknown')} - {result.get('collectionName', 'Unknown')}").classes("text-sm text-gray-400")
                                                        ui.label(f"Year: {result.get('releaseDate', '')[:4] if result.get('releaseDate') else 'Unknown'}").classes("text-xs text-gray-500")
                                                    ui.button(
                                                        "Use",
                                                        icon="check",
                                                        on_click=lambda r=result: apply_itunes_metadata(r)
                                                    ).props("color=primary size=sm")
                                        
                                        ui.separator()
                                        ui.button("Close", on_click=dialog.close).classes("mt-2")
                            except Exception as e:
                                results_container.clear()
                                with results_container:
                                    ui.label(f"Error: {str(e)}").classes("text-red-500")
                                    ui.button("Close", on_click=dialog.close).classes("mt-2")
                            
                            dialog.open()
                    
                    def apply_itunes_metadata(result):
                        """Apply iTunes metadata to form"""
                        metadata_state['title'] = result.get('trackName', metadata_state['title'])
                        metadata_state['artist'] = result.get('artistName', '')
                        metadata_state['album'] = result.get('collectionName', '')
                        if result.get('releaseDate'):
                            metadata_state['year'] = result['releaseDate'][:4]
                        metadata_state['genre'] = result.get('primaryGenreName', '')
                        metadata_state['cover_art_url'] = result.get('artworkUrl100', '').replace('100x100', '600x600')
                        
                        # Update form fields
                        title_input.set_value(metadata_state['title'])
                        artist_input.set_value(metadata_state['artist'])
                        album_input.set_value(metadata_state['album'])
                        year_input.set_value(metadata_state['year'])
                        genre_input.set_value(metadata_state['genre'])
                        if metadata_state['cover_art_url']:
                            cover_preview.set_source(metadata_state['cover_art_url'])
                        
                        ui.notify("Metadata applied from iTunes", type="positive")
                    
                    with ui.row().classes("w-full gap-2 mb-4"):
                        ui.button(
                            "Search iTunes API",
                            icon="search",
                            on_click=search_itunes
                        ).props("color=secondary")
                    
                    # Metadata form
                    with ui.grid(columns=2).classes("w-full gap-4"):
                        artist_input = ui.input(
                            label="Artist",
                            value=metadata_state['artist']
                        ).classes("w-full")
                        artist_input.on("input", lambda e: metadata_state.update(artist=e.value))
                        
                        album_input = ui.input(
                            label="Album",
                            value=metadata_state['album']
                        ).classes("w-full")
                        album_input.on("input", lambda e: metadata_state.update(album=e.value))
                        
                        year_input = ui.input(
                            label="Year",
                            value=metadata_state['year']
                        ).classes("w-full")
                        year_input.on("input", lambda e: metadata_state.update(year=e.value))
                        
                        genre_input = ui.input(
                            label="Genre",
                            value=metadata_state['genre']
                        ).classes("w-full")
                        genre_input.on("input", lambda e: metadata_state.update(genre=e.value))
                    
                    # Cover art
                    ui.label("Cover Art").classes("font-semibold mt-4 mb-2")
                    cover_art_input = ui.input(
                        label="Cover Art URL",
                        value=metadata_state['cover_art_url'],
                        placeholder="Enter URL or leave empty to use iTunes result"
                    ).classes("w-full mb-2")
                    cover_art_input.on("input", lambda e: metadata_state.update(cover_art_url=e.value))
                    
                    cover_preview = ui.image("").classes("w-48 h-48 object-cover rounded border")
                    cover_preview.set_visibility(False)
                    
                    def update_cover_preview():
                        url = cover_art_input.value
                        if url:
                            cover_preview.set_source(url)
                            cover_preview.set_visibility(True)
                        else:
                            cover_preview.set_visibility(False)
                    
                    cover_art_input.on("input", lambda: update_cover_preview())
                    if metadata_state['cover_art_url']:
                        update_cover_preview()
                    
                    # Download and process button
                    async def download_and_process():
                        if not title_input.value:
                            ui.notify("Title is required", type="warning")
                            return
                        
                        # Update metadata state from inputs
                        metadata_state['title'] = title_input.value
                        metadata_state['artist'] = artist_input.value
                        metadata_state['album'] = album_input.value
                        metadata_state['year'] = year_input.value
                        metadata_state['genre'] = genre_input.value
                        metadata_state['cover_art_url'] = cover_art_input.value
                        
                        with ui.dialog() as progress_dialog, ui.card().classes("w-full max-w-md"):
                            ui.label("Processing...").classes("text-lg font-semibold mb-4")
                            progress_label = ui.label("Starting download...").classes("mb-2")
                            progress_bar = ui.linear_progress(value=0).classes("w-full")
                            
                            progress_dialog.open()
                            
                            try:
                                downloader = YouTubeDownloader()
                                
                                # Download audio
                                progress_label.text = "Downloading audio from YouTube..."
                                progress_bar.value = 0.2
                                audio_path = await downloader.download_audio(video_info['url'])
                                
                                # Get metadata and cover art
                                progress_label.text = "Fetching cover art..."
                                progress_bar.value = 0.5
                                cover_art_path = None
                                if metadata_state['cover_art_url']:
                                    cover_art_path = await metadata_manager.download_cover_art(
                                        metadata_state['cover_art_url']
                                    )
                                
                                # Embed metadata
                                progress_label.text = "Embedding metadata..."
                                progress_bar.value = 0.7
                                final_path = await metadata_manager.embed_metadata(
                                    audio_path,
                                    metadata_state,
                                    cover_art_path
                                )
                                
                                # Move to music library
                                progress_label.text = "Moving to music library..."
                                progress_bar.value = 0.9
                                library_path = config.get_music_library_path()
                                final_library_path = await metadata_manager.save_to_library(
                                    final_path,
                                    library_path,
                                    metadata_state
                                )
                                
                                progress_bar.value = 1.0
                                progress_label.text = f"Complete! Saved to: {final_library_path}"
                                
                                ui.notify("Music file successfully added to library!", type="positive")
                                
                                # Clean up temp files
                                if os.path.exists(audio_path):
                                    os.remove(audio_path)
                                if cover_art_path and os.path.exists(cover_art_path):
                                    os.remove(cover_art_path)
                                
                                await asyncio.sleep(2)
                                progress_dialog.close()
                                
                                # Clear selection
                                selected_video_container.clear()
                                
                            except Exception as e:
                                progress_label.text = f"Error: {str(e)}"
                                ui.notify(f"Failed to process: {str(e)}", type="negative")
                                import traceback
                                traceback.print_exc()
                    
                    ui.button(
                        "Download & Add to Library",
                        icon="download",
                        on_click=download_and_process
                    ).classes("w-full mt-4").props("color=primary size=lg")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="LuwefyDL",
        favicon="🎵",
        dark=True,
        port=8080,
        reload=False
    )

