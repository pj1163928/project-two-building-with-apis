"""The one way to tidy a tag name. Every tag, from providers or pack owners, goes through it."""

# The longest tag kept; a longer name is cut to this.
MAX_TAG_LENGTH = 50


def normalize_tag(name: str) -> str | None:
    """Return the tidy form of a tag name, or None when the tag should be dropped.

    The PRD's rules, in order:
    - lowercase, trim and collapse inner whitespace to single spaces
    - drop a tag made only of numbers ("2048"); "2k" stays
    - strip a simple plural "s" from the last word ("Mossy Stones" is
      "mossy stone"), except from words ending in "ss" ("grass")
    A tag with nothing left is dropped. A long one is cut to MAX_TAG_LENGTH.
    """
    words = name.lower().split()
    if not words or "".join(words).isdigit():
        return None
    last = words[-1]
    if last.endswith("s") and not last.endswith("ss"):
        words[-1] = last[:-1]
    tag = " ".join(word for word in words if word)[:MAX_TAG_LENGTH].strip()
    return tag or None
