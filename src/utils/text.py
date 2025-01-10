"""Text processing utility functions."""

def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate long string with ellipsis.
    
    Args:
        text: Original string
        max_length: Maximum length before truncation

    Returns:
        str: Truncated string with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..." 