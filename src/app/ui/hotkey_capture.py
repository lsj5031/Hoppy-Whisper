"""Hotkey capture dialog for the settings and onboarding UI."""

from __future__ import annotations

import logging
from typing import Any, Optional

import customtkinter as ctk

from app.hotkey import (
    HotkeyInUseError,
    HotkeyParseError,
    ensure_hotkey_available,
    parse_hotkey,
)

LOGGER = logging.getLogger("hoppy_whisper.ui.hotkey_capture")

_MODIFIER_ORDER = ("CTRL", "SHIFT", "ALT", "WIN")

_MODIFIER_KEYSYMS = {
    "ctrl": "CTRL",
    "control_l": "CTRL",
    "control_r": "CTRL",
    "shift": "SHIFT",
    "shift_l": "SHIFT",
    "shift_r": "SHIFT",
    "alt": "ALT",
    "alt_l": "ALT",
    "alt_r": "ALT",
    "meta_l": "WIN",
    "meta_r": "WIN",
    "super_l": "WIN",
    "super_r": "WIN",
    "win_l": "WIN",
    "win_r": "WIN",
}

_MODIFIER_KEYCODES = {
    16: "SHIFT",  # VK_SHIFT
    17: "CTRL",  # VK_CONTROL
    18: "ALT",  # VK_MENU
    91: "WIN",  # VK_LWIN
    92: "WIN",  # VK_RWIN
}


def _keycode_to_key_token(keycode: int) -> Optional[str]:
    punctuation = {
        0xBA: ";",
        0xBB: "=",
        0xBC: ",",
        0xBD: "-",
        0xBE: ".",
        0xBF: "/",
        0xC0: "`",
        0xDB: "[",
        0xDC: "\\",
        0xDD: "]",
        0xDE: "'",
    }
    if keycode in punctuation:
        return punctuation[keycode]

    if 0x70 <= keycode <= 0x87:
        return f"F{keycode - 0x70 + 1}"

    named = {
        0x20: "SPACE",
        0x0D: "ENTER",
        0x09: "TAB",
        0x1B: "ESC",
        0x08: "BACKSPACE",
        0x2E: "DELETE",
        0x24: "HOME",
        0x23: "END",
        0x21: "PAGEUP",
        0x22: "PAGEDOWN",
        0x2D: "INSERT",
        0x26: "UP",
        0x28: "DOWN",
        0x25: "LEFT",
        0x27: "RIGHT",
    }
    if keycode in named:
        return named[keycode]

    if 0x30 <= keycode <= 0x39 or 0x41 <= keycode <= 0x5A:
        return chr(keycode)

    return None


def capture_hotkey(
    parent: ctk.CTk,
    *,
    title: str = "Change Hotkey",
    require_modifier: bool = True,
) -> Optional[str]:
    """Prompt the user to press a hotkey chord and return it as text."""
    dialog = HotkeyCaptureDialog(parent, title=title, require_modifier=require_modifier)
    return dialog.get_hotkey()


class HotkeyCaptureDialog(ctk.CTkToplevel):
    """Modal dialog that captures a hotkey chord from the keyboard."""

    def __init__(
        self,
        parent: ctk.CTk,
        *,
        title: str = "Change Hotkey",
        require_modifier: bool = True,
    ) -> None:
        super().__init__(parent)

        self.title(title)
        self.geometry("360x210")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._require_modifier = require_modifier
        self._result: Optional[str] = None
        self._modifiers_down: set[str] = set()

        self._status_var = ctk.StringVar(
            value="Press your new hotkey combination now (Esc to cancel)."
        )
        self._hotkey_var = ctk.StringVar(value="")
        self._error_var = ctk.StringVar(value="")

        ctk.CTkLabel(self, textvariable=self._status_var, wraplength=320).pack(
            padx=20, pady=(18, 10)
        )

        self._capture_entry = ctk.CTkEntry(
            self,
            width=320,
            textvariable=self._hotkey_var,
            font=ctk.CTkFont(family="Consolas", size=14),
            justify="center",
        )
        self._capture_entry.pack(padx=20, pady=(0, 8))
        self._capture_entry.focus_set()

        self._error_label = ctk.CTkLabel(
            self,
            textvariable=self._error_var,
            text_color="#ef4444",
            wraplength=320,
        )
        self._error_label.pack(padx=20, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_cancel,
        ).pack()

        self._capture_entry.bind("<KeyPress>", self._on_key_press)
        self._capture_entry.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.after(0, self._center_on_parent)
        self._update_preview()

    def _center_on_parent(self) -> None:
        parent = self.master
        if not isinstance(parent, ctk.CTk):
            return
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        py = (
            parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        )
        self.geometry(f"+{px}+{py}")

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()

    def get_hotkey(self) -> Optional[str]:
        """Show the dialog and return the captured chord, or None if cancelled."""
        self.wait_window()
        return self._result

    def _on_key_press(self, event: Any) -> str:
        if self._result is not None:
            return "break"

        modifier = self._modifier_from_event(event)
        if modifier:
            self._modifiers_down.add(modifier)
            self._error_var.set("")
            self._update_preview()
            return "break"

        keycode = getattr(event, "keycode", None)
        if not isinstance(keycode, int):
            return "break"

        key_token = _keycode_to_key_token(keycode)
        if key_token is None:
            self._error_var.set(
                "Unsupported key. Try a letter, number, F-key, or common punctuation."
            )
            return "break"

        if self._require_modifier and not self._modifiers_down:
            self._error_var.set("Include at least one modifier (Ctrl/Shift/Alt/Win).")
            self._update_preview()
            return "break"

        chord_text = self._build_chord_text(key_token)
        try:
            chord = parse_hotkey(chord_text)
            if self._require_modifier and chord.modifier_mask == 0:
                raise HotkeyParseError("Hotkey must include at least one modifier")
            ensure_hotkey_available(chord)
        except HotkeyInUseError as exc:
            self._error_var.set(str(exc))
            return "break"
        except HotkeyParseError as exc:
            self._error_var.set(str(exc))
            return "break"
        except Exception as exc:
            LOGGER.debug("Hotkey validation failed", exc_info=exc)
            self._error_var.set(f"Could not validate hotkey: {exc}")
            return "break"

        self._result = chord.display
        self._hotkey_var.set(self._result)
        self.after(10, self.destroy)
        return "break"

    def _on_key_release(self, event: Any) -> str:
        if self._result is not None:
            return "break"

        modifier = self._modifier_from_event(event)
        if modifier and modifier in self._modifiers_down:
            self._modifiers_down.discard(modifier)
            self._update_preview()
        return "break"

    def _modifier_from_event(self, event: Any) -> Optional[str]:
        keysym = getattr(event, "keysym", "")
        if isinstance(keysym, str):
            token = _MODIFIER_KEYSYMS.get(keysym.lower())
            if token:
                return token
        keycode = getattr(event, "keycode", None)
        if isinstance(keycode, int):
            return _MODIFIER_KEYCODES.get(keycode)
        return None

    def _ordered_modifiers(self) -> list[str]:
        return [token for token in _MODIFIER_ORDER if token in self._modifiers_down]

    def _build_chord_text(self, key_token: str) -> str:
        parts = [*self._ordered_modifiers(), key_token]
        return "+".join(parts)

    def _update_preview(self) -> None:
        modifiers = self._ordered_modifiers()
        self._hotkey_var.set("+".join(modifiers) + ("+" if modifiers else ""))
