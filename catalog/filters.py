"""The side panel's filter chips, shared by the library and Discover.

A page's filters are groups of square chips (`catalog/partials/filter_chip.html`),
each a <label> around a hidden checkbox or radio. The library builds its groups
in catalog.library.filter_groups(), Discover in catalog.discover.discover_filter_groups().
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FilterChip:
    """One chip: its value and label, whether it's on, and optionally a count
    (a tag's uses) and icons (a license's symbols, shown before the label)."""

    value: str
    label: str
    checked: bool
    count: int | None = None
    icons: tuple[str, ...] = ()


# Each side-panel filter group's icon, by its name (user request, 2026-11-06).
FILTER_GROUP_ICONS = {
    "type": "shapes",
    "provider": "globe",
    "status": "check",
    "min_rating": "star",
    "tag": "tag",
    "license": "license",
    "commercial": "use-commercial",
}


@dataclass(frozen=True)
class FilterGroup:
    """One group of the side panel's filter chips. `multiple` groups are
    checkboxes (any number on); the others are radios (exactly one).

    A group with a `fold` shows its first `fold` chips and folds the rest
    behind "Show N more" (the Tags group).
    """

    name: str
    title: str
    multiple: bool
    chips: list[FilterChip]
    fold: int = 0

    @property
    def icon(self) -> str:
        """The icon beside the group's label (partials/icon.html)."""
        return FILTER_GROUP_ICONS.get(self.name, "filter")

    @property
    def lead_chips(self) -> list[FilterChip]:
        """The chips always shown."""
        return self.chips[: self.fold] if self.fold else self.chips

    @property
    def more_chips(self) -> list[FilterChip]:
        """The chips folded away until "Show N more" is opened."""
        return self.chips[self.fold :] if self.fold else []

    @property
    def more_open(self) -> bool:
        """Whether the fold starts open: a chosen chip is never hidden."""
        return any(chip.checked for chip in self.more_chips)
