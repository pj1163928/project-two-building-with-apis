"""Small display helpers shared by the providers and the console script."""


def human_size(num_bytes):
    """Format a byte count as B, KB, MB or GB (1 KB = 1024 bytes)."""
    if num_bytes is None:
        return "unknown size"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.2f} GB"


def duration(milliseconds):
    """Format a duration in milliseconds as m:ss."""
    if not milliseconds:
        return "unknown"
    minutes, seconds = divmod(round(milliseconds / 1000), 60)
    return f"{minutes}:{seconds:02d}"
