"""Smart cleanup rule engine for transcribed text."""

from __future__ import annotations

import re
from enum import Enum


class CleanupMode(Enum):
    """Cleanup mode options."""

    CONSERVATIVE = "conservative"
    STANDARD = "standard"
    REWRITE = "rewrite"


class CleanupEngine:
    """Rule-based text cleanup engine with multiple modes."""

    def __init__(self, mode: CleanupMode = CleanupMode.STANDARD) -> None:
        """Initialize the cleanup engine.

        Args:
            mode: The cleanup mode to use (default: STANDARD)
        """
        self.mode = mode

    def clean(self, text: str) -> str:
        """Apply cleanup rules based on the selected mode.

        Args:
            text: Raw transcribed text

        Returns:
            Cleaned text according to the mode
        """
        if not text or not text.strip():
            return ""

        if self.mode == CleanupMode.CONSERVATIVE:
            return self._clean_conservative(text)
        elif self.mode == CleanupMode.STANDARD:
            return self._clean_standard(text)
        elif self.mode == CleanupMode.REWRITE:
            return self._clean_rewrite(text)
        return text

    def _clean_conservative(self, text: str) -> str:
        """Conservative cleanup: minimal changes, preserve most text.

        Rules:
        - Strip leading/trailing whitespace
        - Normalize multiple spaces to single space
        - Preserve URLs, emails, code fragments
        - Basic sentence capitalization
        """
        text = text.strip()

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Capitalize first letter if it's not a URL or email
        if text and not self._starts_with_special(text):
            text = text[0].upper() + text[1:]

        return text

    def _clean_standard(self, text: str) -> str:
        """Standard cleanup: balanced approach for most users.

        Rules:
        - All conservative rules
        - Remove common filler words (um, uh, like, you know)
        - Fix capitalization (sentences, I)
        - Add missing periods at end of sentences
        - Preserve URLs, emails, code
        """
        # Start with conservative
        text = self._clean_conservative(text)

        # Remove filler words (with word boundaries)
        fillers = [
            r"\bum+\b",
            r"\buh+\b",
            r"\buh+m+\b",
            r"\ber+\b",
            r"\blike\b(?! https?://)",  # Don't remove "like" before URLs
        ]
        for filler in fillers:
            text = re.sub(filler, "", text, flags=re.IGNORECASE)

        # Remove common repeated phrases
        text = re.sub(r"\b(you know|I mean)\b", "", text, flags=re.IGNORECASE)

        # Normalize multiple spaces again after removals
        text = re.sub(r"\s+", " ", text).strip()

        # Fix capitalization for "i" when standalone
        text = re.sub(r"\bi\b", "I", text)

        # Ensure sentence starts with capital (unless special case)
        if text and not self._starts_with_special(text):
            text = text[0].upper() + text[1:]

        # Add period at end if missing and text looks like a sentence
        if text and not self._ends_with_punctuation(text):
            text = text + "."

        return text

    def _clean_rewrite(self, text: str) -> str:
        """Rewrite mode: aggressive cleanup for maximum readability.

        Rules:
        - All standard rules
        - Fix common grammatical errors
        - Normalize contractions
        - Fix sentence boundaries
        - More aggressive filler removal
        """
        # Start with standard
        text = self._clean_standard(text)

        # Expand common contractions for clarity
        contractions = {
            r"\bcan't\b": "cannot",
            r"\bwon't\b": "will not",
            r"\bI'm\b": "I am",
            r"\byou're\b": "you are",
            r"\bhe's\b": "he is",
            r"\bshe's\b": "she is",
            r"\bit's\b": "it is",
            r"\bwe're\b": "we are",
            r"\bthey're\b": "they are",
            r"\bdon't\b": "do not",
            r"\bdoesn't\b": "does not",
            r"\bdidn't\b": "did not",
            r"\bwouldn't\b": "would not",
            r"\bshouldn't\b": "should not",
            r"\bcouldn't\b": "could not",
            r"\bisn't\b": "is not",
            r"\baren't\b": "are not",
            r"\bwasn't\b": "was not",
            r"\bweren't\b": "were not",
            r"\bhasn't\b": "has not",
            r"\bhaven't\b": "have not",
            r"\bhadn't\b": "had not",
        }
        for pattern, replacement in contractions.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Remove excessive repetition (same word 2+ times consecutively)
        text = re.sub(r"\b(\w+)(\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)

        return text

    def _starts_with_special(self, text: str) -> bool:
        """Check if text starts with URL, email, or code."""
        if not text:
            return False

        # URL patterns
        if re.match(r"^https?://", text, re.IGNORECASE):
            return True

        # Email patterns
        if re.match(r"^[a-zA-Z0-9_.+-]+@", text):
            return True

        # Code-like patterns (function calls, variables)
        if re.match(r"^[a-z_][a-z0-9_]*\(", text):
            return True

        return False

    def _ends_with_punctuation(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation."""
        if not text:
            return False
        return text[-1] in ".!?;:"
