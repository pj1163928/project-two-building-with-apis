"""A pack's credits: which licenses it holds, what each asks, and the lines to paste.

pack_credits() reads only the pack's items and their stored Assets, like the
manifest, so nothing from a member's library entry can reach it. Its
`required` lines are exactly the manifest's `credits` (every item that isn't
CC0, each line once, in item order), so the pack page, the CREDITS.txt in a
download and the export never disagree. `optional` holds thank-you lines for
the CC0 items, which owe nothing. PackCredits.notice() is the formal
Attribution and License Notice (CREDITS.txt, and the text the pages offer to
copy); credit_lines() is the short version for a credits screen. Anything
with an `.asset` works as an item, so a library entry gets the same notice.
"""

import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from functools import cached_property

from django.utils import timezone

from catalog.licenses import (
    USE_BLOCKED,
    USE_OK,
    USE_STATUS_ICONS,
    USE_STATUS_LABELS,
    USES,
    LicenseInfo,
    license_info,
    worse,
)

from .manifest import credit_line, is_cc0
from .models import PackItem

# Each provider's site, for the optional thank-you lines.
PROVIDER_SITES = {
    "ambientcg": "ambientcg.com",
    "polyhaven": "polyhaven.com",
    "openverse": "openverse.org",
}
NOTICE_TITLE = "ATTRIBUTION AND LICENSE NOTICE"
NOTICE_PREAMBLE = (
    "This notice covers the third-party assets listed below. They are not owned by "
    "the person who compiled them or by Axcenity Toolbox: each remains the work of its "
    "creator and is offered under the license named for it. Anyone who uses, copies, "
    "adapts or distributes these assets, in whole or in part, must do so on the terms "
    "of each asset's license, summarised in section 2."
)
NOTICE_DISCLAIMER = (
    "This notice is a summary prepared for convenience. It is not legal advice and "
    "does not replace or change any license: the license texts linked above are the "
    "binding terms. Licenses are recorded as each provider reported them when the "
    "asset was saved; confirm them on the source pages before release. The assets are "
    'provided by their creators "as is", without warranty of any kind.'
)
NOTICE_FOOTER = "Prepared with Axcenity Toolbox. The asset files are served by their providers."


@dataclass
class LicenseGroup:
    """The pack's items under one license, as the providers wrote it (e.g. "CC BY 4.0")."""

    label: str
    info: LicenseInfo
    url: str
    items: list[PackItem] = field(default_factory=list)

    @property
    def needs_credit(self) -> bool:
        """True when these items are in the required credits (everything but CC0)."""
        return not is_cc0(self.label)


@dataclass
class UseCheck:
    """Whether a whole pack can be used one way (commercial, personal or internal):
    the most restrictive status among its licenses, with one reason per license
    that limits it, the blocking ones first."""

    use: str
    label: str
    description: str
    icon: str
    status: str
    reasons: list[str]

    @property
    def status_label(self) -> str:
        return USE_STATUS_LABELS[self.status]

    @property
    def status_icon(self) -> str:
        return USE_STATUS_ICONS[self.status]

    @property
    def blocked(self) -> bool:
        return self.status == USE_BLOCKED


def _titles(items: Sequence) -> str:
    """'"A"', '"A" and "B"', '"A", "B" and "C"', or '"A", "B" and 3 more'."""
    names = [f'"{item.asset.title}"' for item in items]
    if len(names) > 3:
        return f"{', '.join(names[:2])} and {len(names) - 2} more"
    if len(names) > 1:
        return f"{', '.join(names[:-1])} and {names[-1]}"
    return names[0] if names else ""


def compatibility(groups: Sequence["LicenseGroup"]) -> list[UseCheck]:
    """A pack's UseCheck for each of the USES, from its license groups."""
    checks = []
    for key, label, description, icon in USES:
        status, reasons = USE_OK, []
        for group in groups:
            group_status, note = group.info.use_status(key)
            if group_status == USE_OK:
                continue
            status = worse(status, group_status)
            reasons.append((group_status, f"{_titles(group.items)} ({group.label}): {note}"))
        reasons.sort(key=lambda reason: reason[0] != USE_BLOCKED)
        checks.append(
            UseCheck(key, label, description, icon, status, [text for _, text in reasons])
        )
    return checks


@dataclass
class PackCredits:
    """What a pack's licenses ask: the groups, the lines to paste, and any warnings."""

    groups: list[LicenseGroup]
    required: list[str]
    optional: list[str]
    warnings: list[str]

    @cached_property
    def compatibility(self) -> list[UseCheck]:
        """Can the pack be used commercially, personally, internally? (UseCheck each)."""
        return compatibility(self.groups)

    @property
    def blocked_uses(self) -> list[UseCheck]:
        """The uses some item's license rules out: the pack's warning lists them."""
        return [check for check in self.compatibility if check.blocked]

    @property
    def has_conditions(self) -> bool:
        """True when some use is allowed only with conditions (share-alike, unchanged…)."""
        return any(check.status != USE_OK for check in self.compatibility)

    @property
    def needing_credit(self) -> int:
        """How many items are in the required credits."""
        return sum(len(group.items) for group in self.groups if group.needs_credit)

    def notice(
        self,
        subject: str,
        *,
        compiled_by: str = "",
        source_url: str = "",
        prepared: date | None = None,
    ) -> str:
        """The formal Attribution and License Notice: the CREDITS.txt in every download
        and the text the pages offer to copy.

        `subject` names what it covers (`the pack "Medieval Village"`). It says
        who owns the assets, the credits that must be shown, each license's
        terms (what anyone may do, must do and may not do), the restrictions in
        force, the optional acknowledgements and a disclaimer.
        """
        prepared = prepared or timezone.localdate()
        lines = [NOTICE_TITLE, "=" * len(NOTICE_TITLE), ""]
        lines.append(f"Covers:       {subject}")
        if compiled_by:
            lines.append(f"Compiled by:  {compiled_by}, with Axcenity Toolbox")
        if source_url:
            lines.append(f"Source:       {source_url}")
        lines += [f"Prepared:     {prepared.day} {prepared:%B %Y}", ""]
        lines += _wrap(NOTICE_PREAMBLE)
        lines.append("")
        sections = 0

        def heading(title: str) -> None:
            nonlocal sections
            sections += 1
            lines.append(f"{sections}. {title}")

        heading("REQUIRED ATTRIBUTION")
        if self.required:
            lines += _wrap(
                "The following credits must appear wherever these assets are used or "
                "distributed, for example in a game's credits screen, its documentation "
                "or its store page:",
                indent="   ",
            )
            lines += [f"   - {line}" for line in self.required]
        else:
            lines += _wrap(
                "None. Every asset here is dedicated to the public domain under CC0, so no "
                "attribution is required.",
                indent="   ",
            )
        lines.append("")

        heading("LICENSE TERMS")
        for number, group in enumerate(self.groups, start=1):
            info = group.info
            titles = "; ".join(f'"{item.asset.title}"' for item in group.items)
            lines.append(f"{sections}.{number} {group.label} ({info.title})")
            if group.url:
                lines.append(f"     License:    {group.url}")
            lines += _wrap(f"Applies to: {titles}", indent="     ")
            for label, terms, empty in (
                ("You may:", info.permits, "Nothing until the license is confirmed."),
                ("You must:", info.requires, "Nothing. No conditions apply."),
                ("You may not:", info.prohibits, "No restrictions beyond the law."),
            ):
                lines.append(f"     {label}")
                for term in terms or (empty,):
                    lines += _wrap(term, indent="       - ", hang="         ")
            lines.append("")

        heading("PERMITTED USES")
        for check in self.compatibility:
            lines += _wrap(
                f"{check.label} ({check.description.rstrip('.').lower()}): "
                f"{check.status_label.upper()}.",
                indent="   ",
                hang="     ",
            )
            for reason in check.reasons:
                lines += _wrap(reason, indent="     - ", hang="       ")
        if self.blocked_uses:
            uses = " or ".join(check.label.lower() for check in self.blocked_uses)
            lines += [""] + _wrap(
                f"These assets may not be usable together for {uses} use. Before using "
                "them that way, remove or replace the items listed, or contact the "
                "person who compiled them.",
                indent="   ",
            )
        lines.append("")

        if self.warnings:
            heading("RESTRICTIONS IN FORCE")
            for warning in self.warnings:
                lines += _wrap(warning, indent="   - ", hang="     ")
            lines.append("")

        if self.optional:
            heading("OPTIONAL ACKNOWLEDGEMENTS")
            lines += _wrap(
                "These assets require no attribution. Crediting their creators is welcome "
                "but not required:",
                indent="   ",
            )
            lines += [f"   - {line}" for line in self.optional]
            lines.append("")

        heading("DISCLAIMER")
        lines += _wrap(NOTICE_DISCLAIMER, indent="   ")
        lines += ["", NOTICE_FOOTER, ""]
        return "\n".join(lines)

    def credit_lines(self) -> str:
        """Just the credits, for a game's credits screen: required, then optional."""
        if self.required:
            lines = ["Required credits:", *self.required]
        else:
            lines = ["No credit is required: every asset is CC0."]
        if self.optional:
            lines += ["", "Optional acknowledgements:", *self.optional]
        return "\n".join(lines) + "\n"


def _wrap(text: str, *, indent: str = "", hang: str | None = None) -> list[str]:
    """`text` wrapped at 78 columns, the first line after `indent`, the rest after `hang`."""
    return textwrap.wrap(
        text,
        width=78,
        initial_indent=indent,
        subsequent_indent=indent if hang is None else hang,
        break_on_hyphens=False,
        break_long_words=False,
    )


def courtesy_line(item: PackItem) -> str:
    """A thank-you line for an item that owes no credit: title, author, site, license."""
    asset = item.asset
    site = PROVIDER_SITES.get(asset.provider, asset.get_provider_display())
    author = f" by {asset.author.strip()}" if asset.author.strip() else ""
    return f'"{asset.title}"{author}, from {site} ({asset.license})'


def _warnings(groups: Sequence[LicenseGroup]) -> list[str]:
    def count(test) -> int:
        return sum(len(group.items) for group in groups if test(group.info))

    def items(number: int) -> str:
        return f"{number} item{'s' if number != 1 else ''}"

    warnings = []
    if number := count(lambda info: info.key == "unknown"):
        warnings.append(
            f"{items(number)} {'has' if number == 1 else 'have'} no known license. "
            "Check the source page before you use "
            f"{'it' if number == 1 else 'them'}."
        )
    if number := count(lambda info: info.commercial is False):
        warnings.append(
            f"{items(number)} {'is' if number == 1 else 'are'} non-commercial (NC): "
            "not in a game you sell, or one with ads or paid extras."
        )
    if number := count(lambda info: info.commercial is None and info.key != "unknown"):
        warnings.append(
            f"{items(number)} may be used commercially only when sampled or remixed "
            "(Sampling+), never in adverts."
        )
    if number := count(lambda info: info.changes is False):
        warnings.append(
            f"{items(number)} must be used unchanged (ND): no recolouring, cropping or remixing."
        )
    if number := count(lambda info: info.share_alike):
        warnings.append(
            f"{items(number)} {'is' if number == 1 else 'are'} share-alike (SA): a changed "
            "version must be shared under the same license."
        )
    return warnings


def pack_credits(items: Sequence[PackItem]) -> PackCredits:
    """The credits for a pack's items, given in position order.

    Groups come in the order their license first appears, those needing
    credit first. `required` matches the manifest's `credits` exactly;
    `optional` has one courtesy_line() per CC0 item.
    """
    groups: dict[str, LicenseGroup] = {}
    required: list[str] = []
    optional: list[str] = []
    for item in items:
        asset = item.asset
        label = asset.license.strip() or "unknown"
        group = groups.get(label)
        if group is None:
            group = groups[label] = LicenseGroup(
                label=label,
                info=license_info(label),
                url=asset.license_url or license_info(label).deed_url,
            )
        group.items.append(item)
        if is_cc0(asset.license):
            optional.append(courtesy_line(item))
        else:
            line = credit_line(asset)
            if line not in required:
                required.append(line)
    ordered = sorted(groups.values(), key=lambda group: not group.needs_credit)
    return PackCredits(
        groups=ordered, required=required, optional=optional, warnings=_warnings(ordered)
    )


def pack_notice(pack, credits: PackCredits, source_url: str = "") -> str:
    """The notice for a whole pack, compiled by its owner."""
    return credits.notice(
        f'the pack "{pack.title}"', compiled_by=pack.owner.get_username(), source_url=source_url
    )
