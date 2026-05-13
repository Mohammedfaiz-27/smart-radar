"""
Tamil Text Cleaner Utility
Handles Tamil Unicode issues including orphaned combining marks
Provides Unicode-aware truncation to prevent splitting Tamil characters
"""
import re
import html
import unicodedata
import logging

logger = logging.getLogger(__name__)


# Tamil Unicode ranges
TAMIL_CONSONANTS = range(0x0B95, 0x0BB9 + 1)  # க to ஹ
TAMIL_VOWEL_SIGNS = range(0x0BBE, 0x0BCC + 1)  # ா to ௌ
TAMIL_VIRAMA = 0x0BCD  # ்


def safe_truncate_tamil(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Safely truncate Tamil text without splitting characters.

    This prevents orphaned vowel signs by ensuring we never slice
    between a Tamil consonant and its vowel sign.

    Args:
        text: Text to truncate (may contain Tamil)
        max_length: Maximum length in code points
        suffix: String to append if truncated (default "...")

    Returns:
        Truncated text that doesn't split Tamil characters

    Example:
        >>> text = "பொன்னேரி மாநகராட்சி"
        >>> safe_truncate_tamil(text, 10)  # Won't split மா
        'பொன்னேரி ம...'
    """
    if not text or len(text) <= max_length:
        return text

    # Reserve space for suffix
    actual_max = max_length - len(suffix) if suffix else max_length

    if actual_max <= 0:
        return suffix

    # Start from the desired truncation point
    truncate_pos = actual_max

    # Move backwards to find a safe break point
    # We need to avoid breaking:
    # 1. Between consonant and vowel sign
    # 2. Between consonant and virama
    while truncate_pos > 0:
        char_at_pos = ord(text[truncate_pos]) if truncate_pos < len(text) else 0

        # Check if we're about to split a Tamil vowel sign or virama
        if char_at_pos in TAMIL_VOWEL_SIGNS or char_at_pos == TAMIL_VIRAMA:
            # Move back one position to include the consonant
            truncate_pos -= 1
            continue

        # Check if the character BEFORE is a consonant that might have a vowel sign after
        if truncate_pos > 0:
            prev_char = ord(text[truncate_pos - 1])
            if prev_char in TAMIL_CONSONANTS:
                # Check if current position is a vowel sign
                if char_at_pos in TAMIL_VOWEL_SIGNS or char_at_pos == TAMIL_VIRAMA:
                    truncate_pos -= 1
                    continue

        # Safe to break here
        break

    # Ensure we don't have orphaned marks at the break point
    if truncate_pos < len(text):
        next_char = ord(text[truncate_pos])
        if next_char in TAMIL_VOWEL_SIGNS or next_char == TAMIL_VIRAMA:
            # This shouldn't happen after the above logic, but be safe
            truncate_pos -= 1

    truncated = text[:truncate_pos]

    # Final check: ensure we didn't leave an orphaned mark at the end
    while truncated and truncated[-1:].strip() == '':
        truncated = truncated[:-1]

    return truncated + suffix if suffix else truncated


def clean_tamil_text(text: str, preserve_orphaned: bool = True) -> str:
    """
    Clean and normalize Tamil text.

    Args:
        text: Input text that may contain Tamil characters
        preserve_orphaned: If True, keeps orphaned marks (default). If False, removes them.

    Returns:
        Cleaned and normalized text
    """
    if not text:
        return text

    # Step 1: Unescape any HTML entities
    text = html.unescape(text)

    # Step 2: Normalize to NFC (Canonical Composition)
    text = unicodedata.normalize('NFC', text)

    # Step 3: Optionally remove orphaned marks
    # NOTE: Removing orphaned marks creates incorrect words!
    # e.g., "ாநகராட்சி" -> "நகராட்சி" (WRONG, should be "மாநகராட்சி")
    # By default, we preserve them to avoid creating wrong words
    if not preserve_orphaned:
        # Only use this if you know what you're doing!
        text = re.sub(
            r'(^|[\s\.,;!?\(\)\[\]\{\}"\'])([\u0BBE-\u0BCD]+)',
            r'\1',
            text
        )
        text = re.sub(
            r'(?<![ஃ-௺])([\u0BBE-\u0BCD]+)(?=[\s\.,;!?\(\)\[\]\{\}"\']|$)',
            '',
            text
        )
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

    return text


def validate_tamil_text(text: str) -> bool:
    """
    Validate if Tamil text has orphaned combining marks.

    Args:
        text: Text to validate

    Returns:
        True if text is valid (no orphaned marks), False otherwise
    """
    if not text:
        return True

    # Check for combining marks at word boundaries
    has_orphaned_marks = bool(
        re.search(r'(^|[\s\.,;!?\(\)\[\]\{\}"\'])([\u0BBE-\u0BCD])', text)
    )

    if has_orphaned_marks:
        logger.warning(f"Tamil text has orphaned combining marks: {text[:100]}")
        return False

    return True


def has_orphaned_tamil_marks(text: str) -> bool:
    """
    Check if text has orphaned Tamil combining marks that indicate corruption.

    Returns:
        True if orphaned marks detected (indicates LLM corruption)
    """
    if not text:
        return False

    # Check for combining marks at word boundaries (strong indicator of corruption)
    return bool(re.search(r'(^|[\s\.,;!?\(\)\[\]\{\}"\'])([\u0BBE-\u0BCD])', text))


def remove_corrupted_sentences(text: str) -> str:
    """
    Remove entire sentences that contain ANY corrupted Tamil characters.

    This is more aggressive than preserving corruption - we remove any
    sentence with orphaned vowel signs to ensure clean output.

    Args:
        text: Text that may contain corrupted sentences

    Returns:
        Text with corrupted sentences removed
    """
    if not text:
        return text

    # Split into sentences (Tamil uses । or . or ! or ? as sentence delimiters)
    import re
    sentences = re.split(r'[।.!?।]\s*', text)

    clean_sentences = []
    removed_count = 0

    for sentence in sentences:
        if not sentence.strip():
            continue

        # Check if this sentence has orphaned Tamil marks
        if has_orphaned_tamil_marks(sentence):
            removed_count += 1
            logger.warning(f"Removed corrupted sentence: {sentence[:100]}...")
            continue

        clean_sentences.append(sentence.strip())

    if removed_count > 0:
        logger.info(f"Removed {removed_count} corrupted sentence(s) from text")

    # Join sentences back together
    result = '. '.join(clean_sentences)

    # Add final period if original had one
    if text.rstrip().endswith(('.', '!', '?', '।')):
        result += '.'

    return result


def safe_clean_tamil_content(content: str, field_name: str = "content", remove_corrupted: bool = True) -> str:
    """
    Safely clean Tamil content with aggressive corruption removal.

    Args:
        content: Content to clean
        field_name: Name of field for logging purposes
        remove_corrupted: If True, removes sentences with corruption (default TRUE)

    Returns:
        Cleaned content with corrupted sentences removed
    """
    if not content:
        return content

    # Always normalize Unicode and unescape HTML
    cleaned_content = clean_tamil_text(content, preserve_orphaned=True)

    # Aggressively remove corrupted sentences
    if has_orphaned_tamil_marks(cleaned_content):
        logger.warning(
            f"⚠️ Tamil text corruption detected in {field_name}! "
            f"Original: {cleaned_content[:150]}..."
        )

        if remove_corrupted:
            logger.info(f"🔧 Removing corrupted sentences from {field_name}...")
            cleaned_content = remove_corrupted_sentences(cleaned_content)
            logger.info(f"✅ After removal: {cleaned_content[:150]}...")

            # Check if we still have content after removal
            if not cleaned_content or len(cleaned_content.strip()) < 10:
                logger.error(
                    f"❌ All sentences were corrupted in {field_name}! "
                    f"Returning empty content - LLM needs regeneration."
                )
                return ""
        else:
            logger.warning(f"⚠️ Keeping corrupted content (remove_corrupted=False)")

    return cleaned_content
