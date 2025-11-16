"""
WhiteMagic utility functions.
"""

import re
from datetime import datetime
from typing import List, Tuple, Dict, Any


def now_iso() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO-formatted timestamp string
    """
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str, max_length: int = 50) -> str:
    """
    Convert text to a URL-safe slug.

    Args:
        text: Text to slugify
        max_length: Maximum slug length

    Returns:
        Slugified text
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text[:max_length] or "memory"


def normalize_tags(tags: List[str], normalize: bool = True) -> List[str]:
    """
    Normalize tags to lowercase and remove duplicates.

    Args:
        tags: List of tags to normalize
        normalize: If True, convert to lowercase

    Returns:
        List of normalized tags (no duplicates, ordered)
    """
    if not normalize:
        return [tag.strip() for tag in tags if tag.strip()]

    normalized = []
    seen = set()
    for tag in tags:
        normalized_tag = tag.strip().lower()
        if normalized_tag and normalized_tag not in seen:
            normalized.append(normalized_tag)
            seen.add(normalized_tag)
    return normalized


def clean_markdown(text: str) -> str:
    """
    Clean markdown formatting for context generation.

    Removes headers, bold, italics, links, etc. to get plain text.

    Args:
        text: Markdown text

    Returns:
        Cleaned plain text
    """
    stripped = text.strip()

    # Remove headers
    stripped = re.sub(r"^#{1,6}\s*", "", stripped, flags=re.MULTILINE)

    # Remove bold/italic
    stripped = stripped.replace("**", "")
    stripped = stripped.replace("*", "")
    stripped = stripped.replace("__", "")
    stripped = stripped.replace("_", "")

    # Remove inline code
    stripped = re.sub(r"`[^`]+`", "", stripped)

    # Collapse whitespace
    stripped = re.sub(r"\s+", " ", stripped)

    return stripped.strip()


def truncate_text(text: str, max_chars: int) -> str:
    """
    Truncate text to maximum characters, adding ellipsis if needed.

    Args:
        text: Text to truncate
        max_chars: Maximum characters

    Returns:
        Truncated text
    """
    if not max_chars or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def summarize_text(text: str, max_words: int) -> str:
    """
    Summarize text to maximum words, adding ellipsis if needed.

    Args:
        text: Text to summarize
        max_words: Maximum words

    Returns:
        Summarized text
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def create_preview(text: str, max_chars: int = 240) -> str:
    """
    Create a preview snippet from text.

    Removes line breaks, collapses whitespace, and truncates.

    Args:
        text: Text to preview
        max_chars: Maximum characters

    Returns:
        Preview text
    """
    text = text.strip()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return truncate_text(text, max_chars)


def split_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    """
    Split markdown file into frontmatter and body.

    Expected format:
    ```
    ---
    key: value
    ---
    body content
    ```

    Args:
        raw: Raw file content

    Returns:
        Tuple of (frontmatter dict, body text)
    """
    raw = raw.strip()
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            frontmatter_block = parts[1].strip()
            body = parts[2].strip()
            return parse_frontmatter(frontmatter_block), body
    return {}, raw


def parse_frontmatter(block: str) -> Dict[str, Any]:
    """
    Parse YAML-style frontmatter block.

    Uses PyYAML for proper parsing of YAML structures including:
    - key: value
    - key: [item1, item2]
    - Multi-line lists
    - Nested structures

    Args:
        block: Frontmatter block text

    Returns:
        Dictionary of parsed values
    """
    import yaml
    try:
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        # Fallback to empty dict if YAML is invalid
        return {}


def create_frontmatter(
    title: str,
    timestamp: datetime,
    tags: List[str],
    extra_fields: Dict[str, Any] = None,
) -> str:
    """
    Create YAML-style frontmatter block.

    Args:
        title: Memory title
        timestamp: Creation timestamp
        tags: List of tags
        extra_fields: Additional fields to include

    Returns:
        Formatted frontmatter block with delimiters
    """
    lines = ["---"]
    lines.append(f"title: {title}")
    lines.append(f"created: {timestamp.isoformat(timespec='seconds')}Z")

    if tags:
        tags_str = ", ".join(tags)
        lines.append(f"tags: {tags_str}")

    if extra_fields:
        for key, value in extra_fields.items():
            if key not in ("title", "created", "tags"):
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value)
                    lines.append(f"{key}: {value_str}")
                elif isinstance(value, datetime):
                    lines.append(f"{key}: {value.isoformat(timespec='seconds')}Z")
                else:
                    lines.append(f"{key}: {value}")

    lines.append("---")
    return "\n".join(lines)


def serialize_frontmatter(frontmatter: Dict[str, Any], body: str) -> str:
    """
    Serialize a frontmatter dictionary and body back into a markdown file.
    
    Args:
        frontmatter: Dictionary of frontmatter fields
        body: Markdown body content
    
    Returns:
        Complete markdown file content with frontmatter and body
    """
    import yaml
    lines = ["---"]
    yaml_content = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    lines.append(yaml_content.rstrip())
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def parse_datetime(value: Any) -> datetime:
    """
    Parse various datetime formats into datetime object.

    Args:
        value: Datetime value (string, datetime, or timestamp)

    Returns:
        datetime object

    Raises:
        ValueError: If format is invalid
    """
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        # Remove 'Z' suffix if present
        value = value.rstrip("Z")
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    raise ValueError(f"Cannot parse datetime from: {value}")


def format_size(bytes_size: int) -> str:
    """
    Format byte size in human-readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"
