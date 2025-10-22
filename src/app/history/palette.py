"""History search palette UI using tkinter."""

from __future__ import annotations

import datetime
import json
import logging
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
from typing import Callable, Optional

from .dao import HistoryDAO, Utterance

LOGGER = logging.getLogger("parakeet.history")


class HistoryPalette:
    """Type-ahead search palette for transcription history."""

    def __init__(
        self,
        dao: HistoryDAO,
        on_copy: Callable[[str], None],
        on_paste: Callable[[str], None],
    ) -> None:
        self._dao = dao
        self._on_copy = on_copy
        self._on_paste = on_paste
        self._root: Optional[tk.Tk] = None
        self._search_var: Optional[tk.StringVar] = None
        self._results_listbox: Optional[tk.Listbox] = None
        self._status_label: Optional[ttk.Label] = None
        self._current_results: list[Utterance] = []

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
        self._root = tk.Tk()
        self._root.title("Parakeet History")
        self._root.geometry("700x500")
        self._root.resizable(True, True)

        # Configure grid weights
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        # Search entry
        search_frame = ttk.Frame(self._root, padding="10")
        search_frame.grid(row=0, column=0, sticky="ew")
        search_frame.columnconfigure(0, weight=1)

        ttk.Label(search_frame, text="Search:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)

        search_entry = ttk.Entry(search_frame, textvariable=self._search_var)
        search_entry.grid(row=1, column=0, sticky="ew")
        search_entry.focus_set()

        # Results listbox with scrollbar
        results_frame = ttk.Frame(self._root, padding="10")
        results_frame.grid(row=1, column=0, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Use monospace font for better readability
        list_font = font.Font(family="Consolas", size=10)

        self._results_listbox = tk.Listbox(
            results_frame,
            yscrollcommand=scrollbar.set,
            font=list_font,
            activestyle="dotbox",
            selectmode="single",
            height=15,
        )
        self._results_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self._results_listbox.yview)

        # Button bar
        button_frame = ttk.Frame(self._root, padding="10")
        button_frame.grid(row=2, column=0, sticky="ew")

        ttk.Button(
            button_frame, text="Export to TXT", command=self._on_export_txt
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            button_frame, text="Export to JSON", command=self._on_export_json
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            button_frame, text="Clear History", command=self._on_clear_history
        ).pack(side="left", padx=(0, 5))

        # Status bar
        status_frame = ttk.Frame(self._root, padding="10")
        status_frame.grid(row=3, column=0, sticky="ew")

        status_label = ttk.Label(
            status_frame,
            text="Enter: Copy | Shift+Enter: Paste | Esc: Close",
            foreground="gray",
        )
        self._status_label = status_label
        self._status_label.pack(side="left")

        # Keyboard bindings
        self._root.bind("<Return>", self._on_enter)
        self._root.bind("<Shift-Return>", self._on_shift_enter)
        self._root.bind("<Escape>", self._on_escape)
        self._root.bind("<Up>", self._on_up)
        self._root.bind("<Down>", self._on_down)
        self._results_listbox.bind("<Double-Button-1>", self._on_double_click)

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
        """Load recent utterances into the listbox."""
        try:
            self._current_results = self._dao.get_recent(limit=limit)
            self._update_listbox()
            self._update_status(f"{len(self._current_results)} recent utterances")
        except Exception as exc:
            LOGGER.error("Failed to load recent utterances: %s", exc)
            self._update_status("Error loading history")

    def _on_search_change(self, *_: object) -> None:
        """Handle search text changes."""
        if not self._search_var:
            return

        query = self._search_var.get().strip()
        if not query:
            self._load_recent()
            return

        try:
            self._current_results = self._dao.search(query, limit=50)
            self._update_listbox()
            count = len(self._current_results)
            self._update_status(f"{count} result{'s' if count != 1 else ''} found")
        except Exception as exc:
            LOGGER.error("Search failed: %s", exc)
            self._update_status("Search error")

    def _update_listbox(self) -> None:
        """Update the listbox with current results."""
        if not self._results_listbox:
            return

        self._results_listbox.delete(0, tk.END)
        for utterance in self._current_results:
            # Format: truncate text to 80 chars
            text = utterance.text[:80]
            if len(utterance.text) > 80:
                text += "..."
            self._results_listbox.insert(tk.END, text)

        # Select first item if any
        if self._current_results:
            self._results_listbox.selection_set(0)
            self._results_listbox.activate(0)

    def _update_status(self, message: str) -> None:
        """Update the status label."""
        if self._status_label:
            base_msg = "Enter: Copy | Shift+Enter: Paste | Esc: Close"
            self._status_label.config(text=f"{message} • {base_msg}")

    def _get_selected_utterance(self) -> Optional[Utterance]:
        """Get the currently selected utterance."""
        if not self._results_listbox:
            return None

        selection = self._results_listbox.curselection()
        if not selection:
            return None

        index = selection[0]
        if 0 <= index < len(self._current_results):
            return self._current_results[index]
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

    def _on_up(self, event: object) -> None:
        """Handle Up arrow key."""
        if not self._results_listbox:
            return
        selection = self._results_listbox.curselection()
        if selection:
            index = selection[0]
            if index > 0:
                self._results_listbox.selection_clear(0, tk.END)
                self._results_listbox.selection_set(index - 1)
                self._results_listbox.activate(index - 1)
                self._results_listbox.see(index - 1)

    def _on_down(self, event: object) -> None:
        """Handle Down arrow key."""
        if not self._results_listbox:
            return
        selection = self._results_listbox.curselection()
        if selection:
            index = selection[0]
            if index < self._results_listbox.size() - 1:
                self._results_listbox.selection_clear(0, tk.END)
                self._results_listbox.selection_set(index + 1)
                self._results_listbox.activate(index + 1)
                self._results_listbox.see(index + 1)

    def _on_double_click(self, _event: object = None) -> None:
        """Handle double-click on listbox item - copy."""
        self._on_enter()

    def _on_export_txt(self) -> None:
        """Export history to a text file."""
        try:
            utterances = self._dao.export_all_to_dict()
            if not utterances:
                messagebox.showinfo("Export", "No history to export.")
                return

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"parakeet_history_{timestamp}.txt"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=default_name,
            )

            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("Parakeet Transcription History\n")
                f.write("=" * 60 + "\n\n")
                for utt in utterances:
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

            msg = f"Exported {len(utterances)} utterances to:\n{file_path}"
            messagebox.showinfo("Export Complete", msg)
            LOGGER.info("Exported %d utterances to %s", len(utterances), file_path)

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
            default_name = f"parakeet_history_{timestamp}.json"

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

            msg = f"Exported {len(utterances)} utterances to:\n{file_path}"
            messagebox.showinfo("Export Complete", msg)
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
            self._update_listbox()
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
