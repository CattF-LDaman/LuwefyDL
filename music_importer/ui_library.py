"""NiceGUI panel for browsing and managing the on-disk music library."""

from __future__ import annotations

import os
from nicegui import ui

from music_importer.config import Config
from music_importer.library import LibraryManager, TrackRecord
from music_importer.metadata import MetadataManager


def build_library_panel(config: Config) -> None:
    library_mgr = LibraryManager(config)
    metadata_mgr = MetadataManager(config)
    library_path = config.get_music_library_path()

    state = {
        "tracks": [],
        "selected_path": None,
    }

    with ui.card().classes("w-full p-4"):
        ui.label("Manage Library").classes("text-xl font-semibold mb-4")
        ui.label(f"Library: {library_path}").classes("text-sm text-gray-500 mb-4")

        filter_input = ui.input(
            label="Filter",
            placeholder="Search artist, album, title, or path",
        ).classes("w-full mb-2")

        table = ui.table(
            columns=[
                {"name": "artist", "label": "Artist", "field": "artist", "align": "left"},
                {"name": "album", "label": "Album", "field": "album", "align": "left"},
                {"name": "title", "label": "Title", "field": "title", "align": "left"},
                {"name": "path", "label": "Path", "field": "path", "align": "left"},
            ],
            rows=[],
            row_key="path",
            pagination={"rowsPerPage": 15},
        ).classes("w-full").props("flat dense")

        editor_container = ui.column().classes("w-full mt-4")

        def track_to_row(track: TrackRecord) -> dict:
            display_path = track.path
            if len(display_path) > 80:
                display_path = "…" + display_path[-77:]
            return {
                "artist": track.artist or "—",
                "album": track.album or "—",
                "title": track.title or "—",
                "path": display_path,
                "full_path": track.path,
            }

        def filtered_tracks() -> list:
            query = (filter_input.value or "").strip().lower()
            if not query:
                return state["tracks"]
            result = []
            for t in state["tracks"]:
                haystack = " ".join(
                    [t.artist, t.album, t.title, t.path]
                ).lower()
                if query in haystack:
                    result.append(t)
            return result

        def refresh_table() -> None:
            rows = [track_to_row(t) for t in filtered_tracks()]
            table.rows = rows
            table.update()

        def load_library() -> None:
            state["tracks"] = library_mgr.scan(library_path)
            refresh_table()

        def show_editor(track: TrackRecord) -> None:
            state["selected_path"] = track.path
            editor_container.clear()

            with editor_container:
                with ui.card().classes("w-full p-4"):
                    ui.label("Edit track").classes("text-lg font-semibold mb-2")
                    ui.label(track.path).classes("text-xs text-gray-500 mb-4 break-all")

                    title_input = ui.input("Title", value=track.title).classes("w-full")
                    artist_input = ui.input("Artist", value=track.artist).classes("w-full")
                    album_input = ui.input("Album", value=track.album).classes("w-full")
                    year_input = ui.input("Year", value=track.year).classes("w-full")
                    genre_input = ui.input("Genre", value=track.genre).classes("w-full")
                    cover_url_input = ui.input(
                        "Cover art URL (optional)",
                        placeholder="https://…",
                    ).classes("w-full")

                    with ui.row().classes("w-full gap-2 mt-4"):
                        async def save_changes() -> None:
                            if not title_input.value:
                                ui.notify("Title is required", type="warning")
                                return
                            metadata = {
                                "title": title_input.value,
                                "artist": artist_input.value,
                                "album": album_input.value,
                                "year": year_input.value,
                                "genre": genre_input.value,
                            }
                            cover_path = None
                            if cover_url_input.value:
                                cover_path = await metadata_mgr.download_cover_art(
                                    cover_url_input.value
                                )
                            try:
                                new_path = await library_mgr.update_track(
                                    state["selected_path"],
                                    library_path,
                                    metadata,
                                    cover_path,
                                )
                                if cover_path and os.path.exists(cover_path):
                                    os.remove(cover_path)
                                ui.notify("Track updated", type="positive")
                                load_library()
                                updated = library_mgr.read_track(new_path, library_path)
                                show_editor(updated)
                            except Exception as e:
                                ui.notify(f"Update failed: {e}", type="negative")

                        ui.button("Save changes", icon="save", on_click=save_changes).props(
                            "color=primary"
                        )

                        def open_delete_dialog() -> None:
                            current = state["selected_path"]
                            if not current:
                                return
                            try:
                                to_delete = library_mgr.read_track(current, library_path)
                            except Exception as ex:
                                ui.notify(f"Could not load track: {ex}", type="negative")
                                return
                            with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
                                ui.label("Delete this file permanently?").classes(
                                    "text-lg font-semibold text-red-400"
                                )
                                ui.label(
                                    "This removes the file from disk. This action cannot be undone."
                                ).classes("text-sm text-gray-400 mb-2")
                                ui.label(f"{to_delete.title} — {to_delete.artist}").classes(
                                    "font-medium"
                                )
                                ui.label(current).classes("text-xs break-all text-gray-500 mb-4")

                                with ui.row().classes("w-full justify-end gap-2"):
                                    ui.button("Cancel", on_click=dialog.close).props("flat")

                                    async def confirm_delete() -> None:
                                        try:
                                            library_mgr.delete_track(current, library_path)
                                            dialog.close()
                                            state["selected_path"] = None
                                            editor_container.clear()
                                            load_library()
                                            ui.notify("Track deleted", type="positive")
                                        except Exception as e:
                                            ui.notify(f"Delete failed: {e}", type="negative")

                                    ui.button(
                                        "Delete file",
                                        on_click=confirm_delete,
                                    ).props("color=negative")

                            dialog.open()

                        ui.button("Delete…", icon="delete", on_click=open_delete_dialog).props(
                            "color=negative outline"
                        )

        def on_row_click(e) -> None:
            row = e.args[1]
            full_path = row.get("full_path")
            if not full_path:
                return
            try:
                track = library_mgr.read_track(full_path, library_path)
                show_editor(track)
            except Exception as ex:
                ui.notify(f"Could not load track: {ex}", type="negative")

        table.on("rowClick", on_row_click)

        def on_filter(_=None) -> None:
            refresh_table()

        filter_input.on("input", on_filter)

        with ui.row().classes("w-full gap-2 mb-4"):
            ui.button("Refresh", icon="refresh", on_click=load_library).props(
                "color=primary"
            )

        load_library()
