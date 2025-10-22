"""Unit tests for the cleanup engine (E4.1)."""

from __future__ import annotations

import pytest

from app.cleanup import CleanupEngine, CleanupMode


class TestCleanupEngineConservative:
    """Test conservative cleanup mode."""

    def test_basic_whitespace_normalization(self):
        engine = CleanupEngine(CleanupMode.CONSERVATIVE)
        text = "  hello   world  "
        result = engine.clean(text)
        assert result == "Hello world"

    def test_capitalize_first_letter(self):
        engine = CleanupEngine(CleanupMode.CONSERVATIVE)
        text = "hello world"
        result = engine.clean(text)
        assert result == "Hello world"

    def test_preserve_urls(self):
        engine = CleanupEngine(CleanupMode.CONSERVATIVE)
        text = "https://example.com is a website"
        result = engine.clean(text)
        assert result == "https://example.com is a website"

    def test_preserve_emails(self):
        engine = CleanupEngine(CleanupMode.CONSERVATIVE)
        text = "user@example.com is my email"
        result = engine.clean(text)
        assert result == "user@example.com is my email"

    def test_empty_string(self):
        engine = CleanupEngine(CleanupMode.CONSERVATIVE)
        assert engine.clean("") == ""
        assert engine.clean("   ") == ""


class TestCleanupEngineStandard:
    """Test standard cleanup mode."""

    def test_remove_filler_words(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "um I think uh we should um do this"
        result = engine.clean(text)
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "I think" in result

    def test_fix_standalone_i(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "i think i can do it"
        result = engine.clean(text)
        assert result == "I think I can do it."

    def test_add_period_at_end(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "this is a sentence"
        result = engine.clean(text)
        assert result.endswith(".")

    def test_no_duplicate_period(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "this is a sentence."
        result = engine.clean(text)
        assert result == "This is a sentence."
        assert result.count(".") == 1

    def test_preserve_question_mark(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "is this a question?"
        result = engine.clean(text)
        assert result == "Is this a question?"
        assert not result.endswith(".?")

    def test_remove_you_know(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "you know I think you know this works"
        result = engine.clean(text)
        assert "you know" not in result.lower()

    def test_preserve_like_in_url(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "I like https://example.com"
        result = engine.clean(text)
        # "like" before URL should be preserved
        assert "https://example.com" in result


class TestCleanupEngineRewrite:
    """Test rewrite cleanup mode."""

    def test_expand_contractions(self):
        engine = CleanupEngine(CleanupMode.REWRITE)
        text = "I can't do it because I'm tired"
        result = engine.clean(text)
        assert "cannot" in result
        assert "I am" in result
        assert "can't" not in result
        assert "I'm" not in result

    def test_remove_repetition(self):
        engine = CleanupEngine(CleanupMode.REWRITE)
        text = "the the the test"
        result = engine.clean(text)
        # Should remove excessive repetition (3x "the" becomes 1x "the")
        assert result == "The test."

    def test_all_contractions(self):
        engine = CleanupEngine(CleanupMode.REWRITE)
        text = "it's not what you're thinking"
        result = engine.clean(text)
        assert "it is" in result or "It is" in result
        assert "you are" in result
        assert "it's" not in result
        assert "you're" not in result


class TestCleanupEngineEdgeCases:
    """Test edge cases and special scenarios."""

    def test_code_snippet(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "function(arg1, arg2) is the syntax"
        result = engine.clean(text)
        # Should preserve function call syntax
        assert "function(arg1, arg2)" in result

    def test_url_with_path(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "https://example.com/path/to/page is the link"
        result = engine.clean(text)
        assert "https://example.com/path/to/page" in result

    def test_mixed_punctuation(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "hello world!"
        result = engine.clean(text)
        assert result == "Hello world!"
        assert not result.endswith(".!")

    def test_numbers_preserved(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "the answer is 42"
        result = engine.clean(text)
        assert "42" in result

    def test_multiple_sentences(self):
        engine = CleanupEngine(CleanupMode.STANDARD)
        text = "first sentence. second sentence"
        result = engine.clean(text)
        assert result.startswith("First")
        # Should preserve existing period
        assert ". " in result or result.endswith(".")


class TestCleanupModes:
    """Test mode selection and behavior differences."""

    def test_conservative_keeps_fillers(self):
        conservative = CleanupEngine(CleanupMode.CONSERVATIVE)
        text = "um hello world"
        result = conservative.clean(text)
        # Conservative should keep "um"
        assert "um" in result.lower()

    def test_standard_removes_fillers(self):
        standard = CleanupEngine(CleanupMode.STANDARD)
        text = "um hello world"
        result = standard.clean(text)
        # Standard should remove "um"
        assert "um" not in result.lower()

    def test_rewrite_expands_contractions(self):
        standard = CleanupEngine(CleanupMode.STANDARD)
        rewrite = CleanupEngine(CleanupMode.REWRITE)

        text = "I can't do it"

        standard_result = standard.clean(text)
        rewrite_result = rewrite.clean(text)

        # Standard keeps contractions
        assert "can't" in standard_result or "cannot" in standard_result

        # Rewrite expands them
        assert "cannot" in rewrite_result
        assert "can't" not in rewrite_result


@pytest.mark.parametrize(
    "mode,input_text,expected_output",
    [
        (CleanupMode.CONSERVATIVE, "hello world", "Hello world"),
        (CleanupMode.STANDARD, "um hello world", "Hello world."),
        (CleanupMode.REWRITE, "I'm here", "I am here."),
    ],
)
def test_mode_examples(mode, input_text, expected_output):
    """Parametrized test for different modes."""
    engine = CleanupEngine(mode)
    result = engine.clean(input_text)
    assert result == expected_output
