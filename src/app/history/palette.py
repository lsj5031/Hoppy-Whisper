"""History search palette UI using customtkinter."""

from __future__ import annotations

import datetime
import json
import logging
import threading
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from .dao import HistoryDAO, Utterance

LOGGER = logging.getLogger("hoppy_whisper.history")


class HistoryPalette:
    """Type-ahead search palette for transcription history with modern UI."""

    ACCENT_COLOR = "#3b82f6"

    def __init__(
        self,
        dao: HistoryDAO,
        on_copy: Callable[[str], None],
        on_paste: Callable[[str], None],
    ) -> None:
        self._dao = dao
        self._on_copy = on_copy
        self._on_paste = on_paste
        self._root: Optional[ctk.CTk] = None
        self._search_var: Optional[ctk.StringVar] = None
        self._results_frame: Optional[ctk.CTkScrollableFrame] = None
        self._status_label: Optional[ctk.CTkLabel] = None
        self._current_results: list[Utterance] = []
        self._selected_index: int = 0
        self._result_buttons: list[ctk.CTkButton] = []
        # Background search state
        self._search_thread: Optional[threading.Thread] = None
        self._search_cancelled = False

    def show(self) -> None:
        """Open the history palette window."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return

        self._create_window()
        self._load_recent()
        if self._root:
            self._root.mainloop()

    def _create_window(self) -> None:
        """Create the palette window and widgets."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title("Hoppy Whisper History")
        self._root.geometry("750x550")
        self._root.resizable(True, True)
        self._root.minsize(500, 400)

        # Main container
        main_frame = ctk.CTkFrame(self._root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="📚 Transcription History",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Search frame
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="e")

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)

        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self._search_var,
            placeholder_text="Search transcriptions...",
            width=250,
            height=36,
        )
        search_entry.grid(row=0, column=0)
        search_entry.focus_set()

        # Results frame (scrollable)
        results_container = ctk.CTkFrame(main_frame, corner_radius=12)
        results_container.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        results_container.grid_columnconfigure(0, weight=1)
        results_container.grid_rowconfigure(0, weight=1)

        self._results_frame = ctk.CTkScrollableFrame(
            results_container,
            fg_color="transparent",
        )
        self._results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self._results_frame.grid_columnconfigure(0, weight=1)

        # Button bar
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(
            button_frame,
            text="Export TXT",
            width=110,
            command=self._on_export_txt,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            button_frame,
            text="Export JSON",
            width=110,
            command=self._on_export_json,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            button_frame,
            text="Clear History",
            width=110,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._on_clear_history,
        ).pack(side="left")

        # Status bar
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.grid(row=3, column=0, sticky="ew")

        self._status_label = ctk.CTkLabel(
            status_frame,
            text="Click to copy • Double-click to paste • Esc to close",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self._status_label.pack(side="left")

        # Keyboard bindings
        self._root.bind("<Escape>", self._on_escape)
        self._root.bind("<Up>", self._on_up)
        self._root.bind("<Down>", self._on_down)
        self._root.bind("<Return>", self._on_enter)
        self._root.bind("<Shift-Return>", self._on_shift_enter)

        # Center window on screen
        self._center_window()

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self) -> None:
        """Center the window on the screen."""
        if not self._root:
            return
        self._root.update_idletasks()
        width = self._root.winfo_width()
        height = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (width // 2)
        y = (self._root.winfo_screenheight() // 2) - (height // 2)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _load_recent(self, limit: int = 50) -> None:
        """Load recent utterances into the results."""
        try:
            self._current_results = self._dao.get_recent(limit=limit)
            self._update_results()
            self._update_status(f"{len(self._current_results)} recent transcriptions")
        except Exception as exc:
            LOGGER.error("Failed to load recent utterances: %s", exc)
            self._update_status("Error loading history")

    def _on_search_change(self, *_: object) -> None:
        """Handle search text changes with non-blocking background search."""
        if not self._search_var:
            return

        query = self._search_var.get().strip()
        self._search_cancelled = True

        if not query:
            self._load_recent()
            return

        def _background_search() -> None:
            """Run search in background thread."""
            try:
                results = self._dao.search(query, limit=50)
                if (
                    self._root
                    and self._root.winfo_exists()
                    and not self._search_cancelled
                ):
                    self._root.after(
                        0, lambda: self._update_search_results(results, query)
                    )
            except Exception as exc:
                LOGGER.error("Background search failed: %s", exc)
                if self._root and self._root.winfo_exists():
                    self._root.after(0, lambda: self._update_status("Search error"))

        self._search_cancelled = False
        self._search_thread = threading.Thread(target=_background_search, daemon=True)
        self._search_thread.start()

    def _update_search_results(self, results: list[Utterance], query: str) -> None:
        """Update UI with search results. Called on main thread."""
        if self._search_cancelled or not self._search_var:
            return
        if self._search_var.get().strip() != query:
            return
        self._current_results = results
        self._update_results()
        count = len(results)
        self._update_status(f"{count} result{'s' if count != 1 else ''} found")

    def _update_results(self) -> None:
        """Update the results display with current results."""
        if not self._results_frame:
            return

        # Clear existing results
        for widget in self._results_frame.winfo_children():
            widget.destroy()
        self._result_buttons.clear()
        self._selected_index = 0

        if not self._current_results:
            empty_label = ctk.CTkLabel(
                self._results_frame,
                text="No transcriptions found",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            )
            empty_label.pack(pady=40)
            return

        for i, utterance in enumerate(self._current_results):
            self._create_result_item(i, utterance)

        # Select first item
        if self._result_buttons:
            self._select_item(0)

    def _create_result_item(self, index: int, utterance: Utterance) -> None:
        """Create a result item widget."""
        # Container frame
        item_frame = ctk.CTkFrame(
            self._results_frame,
            corner_radius=8,
            fg_color=("gray90", "gray17"),
        )
        item_frame.pack(fill="x", pady=3, padx=2)
        item_frame.grid_columnconfigure(0, weight=1)

        # Text preview (truncated)
        text = utterance.text[:100]
        if len(utterance.text) > 100:
            text += "..."

        text_button = ctk.CTkButton(
            item_frame,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray25"),
            anchor="w",
            height=40,
            command=lambda idx=index: self._on_item_click(idx),
        )
        text_button.pack(fill="x", padx=5, pady=5)
        self._result_buttons.append(text_button)

        # Bind double-click for paste
        text_button.bind(
            "<Double-Button-1>",
            lambda e, idx=index: self._on_item_double_click(idx),
        )

        # Metadata row
        meta_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        meta_frame.pack(fill="x", padx=10, pady=(0, 8))

        # Timestamp
        dt = datetime.datetime.fromtimestamp(utterance.created_utc)
        time_str = dt.strftime("%Y-%m-%d %H:%M")

        ctk.CTkLabel(
            meta_frame,
            text=time_str,
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(side="left")

        # Duration
        if utterance.duration_ms:
            duration_sec = utterance.duration_ms / 1000
            ctk.CTkLabel(
                meta_frame,
                text=f"• {duration_sec:.1f}s",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            ).pack(side="left", padx=(10, 0))

        # Mode
        ctk.CTkLabel(
            meta_frame,
            text=f"• {utterance.mode}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(side="left", padx=(10, 0))

    def _select_item(self, index: int) -> None:
        """Select an item by index."""
        if not self._result_buttons:
            return

        # Deselect previous
        if 0 <= self._selected_index < len(self._result_buttons):
            self._result_buttons[self._selected_index].configure(fg_color="transparent")

        # Select new
        self._selected_index = max(0, min(index, len(self._result_buttons) - 1))
        if 0 <= self._selected_index < len(self._result_buttons):
            self._result_buttons[self._selected_index].configure(
                fg_color=("gray80", "gray25")
            )

    def _on_item_click(self, index: int) -> None:
        """Handle single click on item - copy to clipboard."""
        if 0 <= index < len(self._current_results):
            self._select_item(index)
            utterance = self._current_results[index]
            self._on_copy(utterance.text)
            self._update_status("Copied to clipboard")
            LOGGER.debug("Copied utterance %d to clipboard", utterance.id)

    def _on_item_double_click(self, index: int) -> None:
        """Handle double click on item - paste."""
        if 0 <= index < len(self._current_results):
            utterance = self._current_results[index]
            self._on_paste(utterance.text)
            self._update_status("Pasted")
            LOGGER.debug("Pasted utterance %d", utterance.id)
            self._on_close()

    def _update_status(self, message: str) -> None:
        """Update the status label."""
        if self._status_label:
            base_msg = "Click to copy • Double-click to paste • Esc to close"
            self._status_label.configure(text=f"{message} • {base_msg}")

    def _get_selected_utterance(self) -> Optional[Utterance]:
        """Get the currently selected utterance."""
        if 0 <= self._selected_index < len(self._current_results):
            return self._current_results[self._selected_index]
        return None

    def _on_enter(self, _event: object = None) -> None:
        """Handle Enter key - copy selected text."""
        utterance = self._get_selected_utterance()
        if utterance:
            self._on_copy(utterance.text)
            self._update_status("Copied to clipboard")
            LOGGER.debug("Copied utterance %d to clipboard", utterance.id)

    def _on_shift_enter(self, _event: object = None) -> None:
        """Handle Shift+Enter - paste selected text."""
        utterance = self._get_selected_utterance()
        if utterance:
            self._on_paste(utterance.text)
            self._update_status("Pasted")
            LOGGER.debug("Pasted utterance %d", utterance.id)
            self._on_close()

    def _on_escape(self, _event: object = None) -> None:
        """Handle Escape key - close window."""
        self._on_close()

    def _on_up(self, _event: object = None) -> None:
        """Handle Up arrow key."""
        if self._selected_index > 0:
            self._select_item(self._selected_index - 1)

    def _on_down(self, _event: object = None) -> None:
        """Handle Down arrow key."""
        if self._selected_index < len(self._result_buttons) - 1:
            self._select_item(self._selected_index + 1)

    def _on_export_txt(self) -> None:
        """Export history to a text file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"hoppy_whisper_history_{timestamp}.txt"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=default_name,
            )

            if not file_path:
                return

            count = 0
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("Hoppy Whisper Transcription History\n")
                f.write("=" * 60 + "\n\n")
                for utt in self._dao.iter_utterances(batch_size=500):
                    count += 1
                    created_utc = utt["created_utc"]
                    if not isinstance(created_utc, (int, float)):
                        msg = f"Expected int/float, got {type(created_utc)}"
                        raise TypeError(msg)
                    dt = datetime.datetime.fromtimestamp(created_utc)
                    f.write(f"ID: {utt['id']}\n")
                    f.write(f"Date: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Mode: {utt['mode']}\n")
                    if utt["duration_ms"]:
                        f.write(f"Duration: {utt['duration_ms']}ms\n")
                    f.write(f"Text: {utt['text']}\n")
                    if utt["raw_text"]:
                        f.write(f"Raw: {utt['raw_text']}\n")
                    f.write("\n" + "-" * 60 + "\n\n")

            if count == 0:
                messagebox.showinfo("Export", "No history to export.")
                return

            messagebox.showinfo(
                "Export Complete", f"Exported {count} utterances to:\n{file_path}"
            )
            LOGGER.info("Exported %d utterances to %s", count, file_path)

        except Exception as exc:
            LOGGER.error("Export to TXT failed: %s", exc)
            messagebox.showerror("Export Failed", f"Failed to export history:\n{exc}")

    def _on_export_json(self) -> None:
        """Export history to a JSON file."""
        try:
            utterances = self._dao.export_all_to_dict()
            if not utterances:
                messagebox.showinfo("Export", "No history to export.")
                return

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"hoppy_whisper_history_{timestamp}.json"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=default_name,
            )

            if not file_path:
                return

            export_data = {
                "exported_at": datetime.datetime.now().isoformat(),
                "count": len(utterances),
                "utterances": utterances,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Export Complete",
                f"Exported {len(utterances)} utterances to:\n{file_path}",
            )
            LOGGER.info("Exported %d utterances to %s", len(utterances), file_path)

        except Exception as exc:
            LOGGER.error("Export to JSON failed: %s", exc)
            messagebox.showerror("Export Failed", f"Failed to export history:\n{exc}")

    def _on_clear_history(self) -> None:
        """Clear all history with confirmation."""
        count = self._dao.count()
        if count == 0:
            messagebox.showinfo("Clear History", "History is already empty.")
            return

        result = messagebox.askyesno(
            "Clear History",
            f"Are you sure you want to delete all {count} utterances?\n\n"
            "This action cannot be undone.",
            icon="warning",
        )

        if not result:
            return

        try:
            deleted = self._dao.clear_all()
            self._current_results = []
            self._update_results()
            self._update_status(f"Deleted {deleted} utterances")
            messagebox.showinfo(
                "Clear History", f"Successfully deleted {deleted} utterances."
            )
            LOGGER.info("Cleared %d utterances from history", deleted)

        except Exception as exc:
            LOGGER.error("Failed to clear history: %s", exc)
            messagebox.showerror("Clear Failed", f"Failed to clear history:\n{exc}")

    def _on_close(self) -> None:
        """Close the palette window."""
        if self._root:
            self._root.quit()
            self._root.destroy()
            self._root = None
