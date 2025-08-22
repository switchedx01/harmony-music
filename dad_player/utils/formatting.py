# dad_player/utils/formatting.py


def format_duration(seconds: float | None) -> str:
    """Formats a duration in seconds into a MM:SS string."""
    if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
        return "0:00"
        
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}:{remaining_seconds:02d}"