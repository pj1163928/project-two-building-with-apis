"""normalize_tag(): the one way every tag name is tidied (PRD, "Data model")."""

import pytest

from catalog.tags import normalize_tag


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Case and surrounding whitespace.
        ("Brick", "brick"),
        ("  WOOD\t", "wood"),
        # Inner whitespace collapses to single spaces.
        ("mossy   \t stone", "mossy stone"),
        # Tags that are only numbers are dropped; numbers with letters stay.
        ("2048", None),
        (" 4 096 ", None),
        ("2k", "2k"),
        # A simple plural "s" comes off (the last word's, for a phrase)...
        ("Rocks", "rock"),
        ("Mossy  Stones", "mossy stone"),
        # ...but words ending in "ss" keep theirs.
        ("grass", "grass"),
        ("Moss", "moss"),
        ("stained glass", "stained glass"),
        # Nothing left means no tag.
        ("", None),
        ("   ", None),
        ("s", None),
    ],
)
def test_normalize_tag_applies_each_rule(raw, expected):
    assert normalize_tag(raw) == expected
