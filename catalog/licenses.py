"""What each license an asset can carry means, in plain words.

The providers write licenses as text: ambientCG and Poly Haven say "CC0 1.0",
and Openverse says "CC BY 4.0", "CC BY-NC-SA 3.0", "Public Domain Mark",
"CC SAMPLING+ 1.0" and so on (providers.openverse.license_label()).
license_info() reads that text and returns the matching LicenseInfo: what the
license lets you do, whether it asks for credit, and how to meet it. The pack
page's credits, the Attribution center and the asset pages all use it, so the
advice is written once.

This is a plain-language guide, not legal advice; the license deed is what
counts, and every card links to it.
"""

import re
from dataclasses import dataclass

# How a license treats credit. "required": the license asks for it.
# "listed": not required by law, but the Toolbox lists it with the required
# credits anyway (the manifest credits everything that isn't CC0).
# "optional": nothing is owed; a thank-you is a kind extra.
CREDIT_REQUIRED = "required"
CREDIT_LISTED = "listed"
CREDIT_OPTIONAL = "optional"

CREDIT_LABELS = {
    CREDIT_REQUIRED: "Credit required",
    CREDIT_LISTED: "Credit recommended",
    CREDIT_OPTIONAL: "Credit optional",
}

# The three ways a project can use an asset, for "Can I use it?" and each pack's
# compatibility: (key, label, what it covers, icon).
USES = (
    ("commercial", "Commercial", "Sold, ad-supported, or made for a business.", "use-commercial"),
    ("personal", "Personal", "Free, non-commercial projects you share or publish.", "use-personal"),
    (
        "internal",
        "Internal",
        "Private use and testing, never shared outside your team.",
        "use-internal",
    ),
)
USE_OK = "ok"
USE_CAUTION = "caution"
USE_BLOCKED = "blocked"
USE_STATUS_LABELS = {USE_OK: "Usable", USE_CAUTION: "With conditions", USE_BLOCKED: "Not usable"}
USE_STATUS_ICONS = {USE_OK: "check", USE_CAUTION: "alert", USE_BLOCKED: "close"}
_USE_RANK = {USE_OK: 0, USE_CAUTION: 1, USE_BLOCKED: 2}

# Each license element's symbol (an icon in partials/icon.html), name and meaning.
SYMBOLS = {
    "zero": ("lic-zero", "Public domain dedication", "The creator gave up every right."),
    "pd": ("lic-pd", "Public domain mark", "Marked as free of known copyright."),
    "by": ("lic-by", "Attribution", "Credit the creator."),
    "sa": ("lic-sa", "ShareAlike", "Share changed versions under the same license."),
    "nc": ("lic-nc", "NonCommercial", "Never in anything commercial."),
    "nd": ("lic-nd", "NoDerivatives", "Use it only unchanged."),
    "sampling": ("lic-sampling", "Sampling", "Sample and remix it into something new."),
    "unknown": ("lic-unknown", "Unknown license", "Check the source before any use."),
}
_LICENSE_SYMBOLS = {
    "cc0": ("zero",),
    "pdm": ("pd",),
    "by": ("by",),
    "by-sa": ("by", "sa"),
    "by-nd": ("by", "nd"),
    "by-nc": ("by", "nc"),
    "by-nc-sa": ("by", "nc", "sa"),
    "by-nc-nd": ("by", "nc", "nd"),
    "sampling+": ("by", "sampling"),
    "nc-sampling+": ("by", "nc", "sampling"),
    "unknown": ("unknown",),
}


@dataclass(frozen=True)
class UseVerdict:
    """Whether a license (or a pack) can be used one way: `status` is USE_OK,
    USE_CAUTION or USE_BLOCKED, and `note` says why, in a short sentence."""

    use: str
    label: str
    description: str
    icon: str
    status: str
    note: str

    @property
    def status_label(self) -> str:
        return USE_STATUS_LABELS[self.status]

    @property
    def status_icon(self) -> str:
        return USE_STATUS_ICONS[self.status]


def worse(first: str, second: str) -> str:
    """The more restrictive of two use statuses."""
    return first if _USE_RANK[first] >= _USE_RANK[second] else second


_HOW_TO_CREDIT = (
    "Credit the creator with the title, the author, where it came from and the "
    "license, with a link to the license (title, author, source, license).",
    "If you changed it (recoloured, cropped, cut or remixed it), say so, for "
    "example “edited from …”.",
    "Put the credit where players can find it: the game's credits screen, its "
    "README, or its store page.",
)
_NONCOMMERCIAL = (
    "Only in a project that isn't commercial: no selling the game, no paid "
    "downloads or DLC, and no ads or sponsorship around it."
)
_NO_CHANGES = (
    "Use it unchanged: no recolouring, cropping, cutting or remixing. "
    "Converting the file format is fine."
)
_SHARE_ALIKE = (
    "If you share a changed version of the asset itself, release that version "
    "under the same license. Using it unchanged beside your own work doesn't "
    "put your whole game under it."
)


@dataclass(frozen=True)
class LicenseInfo:
    """One license family: what it lets you do and what it asks in return.

    `commercial` and `changes` are True (yes), False (no) or None (only in
    part, explained in `summary`). `steps` say how to meet the license.
    """

    key: str
    name: str
    title: str
    summary: str
    credit: str
    commercial: bool | None
    changes: bool | None
    share_alike: bool
    steps: tuple[str, ...]
    deed_url: str

    @property
    def anchor(self) -> str:
        """The id of its card in the Attribution center's guide."""
        return "license-" + self.key.replace("+", "-plus")

    @property
    def credit_label(self) -> str:
        return CREDIT_LABELS[self.credit]

    @property
    def needs_credit(self) -> bool:
        """True unless nothing is owed (CC0)."""
        return self.credit != CREDIT_OPTIONAL

    @property
    def symbols(self) -> list[tuple[str, str, str]]:
        """The license's symbols as (icon, name, meaning): CC BY-NC-SA is
        attribution, non-commercial and share-alike."""
        return [SYMBOLS[key] for key in _LICENSE_SYMBOLS[self.key]]

    def use_status(self, use: str) -> tuple[str, str]:
        """(status, note) for using the license one of the USES ways."""
        if self.key == "unknown":
            if use == "internal":
                return USE_CAUTION, "Confirm the license before relying on it."
            return USE_BLOCKED, "The license is unknown."
        credit = "With credit." if self.credit == CREDIT_REQUIRED else "No conditions."
        if use == "internal":
            if self.commercial is False:
                return USE_CAUTION, "Private testing only, not to build a commercial product."
            if self.credit == CREDIT_REQUIRED:
                return USE_OK, "Credit is needed once you share it."
            return USE_OK, "No conditions."
        if use == "commercial":
            if self.commercial is False:
                return USE_BLOCKED, "Non-commercial only."
            if self.commercial is None:
                return USE_CAUTION, "Only sampled or remixed, never in adverts."
        if self.changes is False:
            return USE_CAUTION, "Unchanged only. " + credit
        if self.share_alike:
            return USE_CAUTION, "Share changed versions alike. " + credit
        return USE_OK, credit

    @property
    def uses(self) -> list[UseVerdict]:
        """The license's verdict for each of the USES, in order."""
        return [
            UseVerdict(key, label, description, icon, *self.use_status(key))
            for key, label, description, icon in USES
        ]

    # The formal terms: what anyone using the asset may do, must do and may not
    # do. The attribution notice (packs.credits) and every license card list them.

    @property
    def permits(self) -> tuple[str, ...]:
        """What the license allows, in the notice's "You may" list."""
        if self.key == "unknown":
            return ()
        terms = ["Copy, use and share the asset in any medium or format."]
        if self.key in ("sampling+", "nc-sampling+"):
            terms.append("Sample, cut, remix and transform it into a new work.")
            if self.commercial is None:
                terms.append("Use a sampled or transformed version in a commercial work.")
            return tuple(terms)
        if self.changes:
            terms.append("Adapt it: change, remix, recolour, crop and build upon it.")
        else:
            terms.append("Convert it to another file format, which isn't a change to the work.")
        if self.commercial:
            terms.append("Use it for any purpose, including commercially, as in a game you sell.")
        else:
            terms.append("Use it in non-commercial projects.")
        return tuple(terms)

    @property
    def requires(self) -> tuple[str, ...]:
        """What the license asks of everyone who uses it, in the "You must" list."""
        if self.key == "unknown":
            return ("Confirm the asset's license on its source page before any use.",)
        if self.credit == CREDIT_OPTIONAL:
            return ()
        if self.credit == CREDIT_LISTED:
            return (
                "Nothing by law. Naming the work and its source, as this notice does, is "
                "recommended because the mark is a label, not a guarantee.",
            )
        terms = [
            "Give appropriate credit: the title, the creator, the source and the license, "
            "with a link to the license, wherever the asset is used or shared.",
            "Keep any copyright, license and disclaimer notices that come with the asset.",
        ]
        if self.changes is not False:
            terms.append("State that you changed the asset, if you did.")
        if self.share_alike:
            terms.append(
                "Share any adapted version of the asset under the same license, or a "
                "compatible one."
            )
        return tuple(terms)

    @property
    def prohibits(self) -> tuple[str, ...]:
        """What the license forbids, in the "You may not" list."""
        if self.key == "unknown":
            return ("Use, change or share the asset until its license is confirmed.",)
        terms = []
        if self.key == "sampling+":
            terms.append("Use the whole work unchanged for commercial purposes.")
            terms.append("Use the work, changed or not, to advertise or promote anything.")
        elif self.commercial is False:
            terms.append(
                "Use it commercially: in a game or product that's sold, in paid downloads "
                "or DLC, or with advertising or sponsorship."
            )
        if self.key == "nc-sampling+":
            terms.append("Use the work, changed or not, to advertise or promote anything.")
        if self.changes is False:
            terms.append(
                "Share an adapted version: anything recoloured, cropped, cut, remixed or "
                "otherwise changed."
            )
        if self.credit == CREDIT_REQUIRED:
            terms.append(
                "Add terms or technical measures that stop others from using the asset as "
                "its license allows."
            )
        terms.append("Suggest that the creator endorses you, your project or your use of it.")
        return tuple(terms)


LICENSES: dict[str, LicenseInfo] = {
    info.key: info
    for info in (
        LicenseInfo(
            key="cc0",
            name="CC0",
            title="Public domain dedication",
            summary="The creator gave up their rights. Use it for anything, sell it in a "
            "game, change it freely. No credit is needed.",
            credit=CREDIT_OPTIONAL,
            commercial=True,
            changes=True,
            share_alike=False,
            steps=(
                "Nothing is required.",
                "Thanking the creator and the site you found it on is a kind extra: see "
                "Optional credits.",
            ),
            deed_url="https://creativecommons.org/publicdomain/zero/1.0/",
        ),
        LicenseInfo(
            key="pdm",
            name="Public Domain Mark",
            title="Marked as public domain",
            summary="Marked as free of known copyright, so you can use and change it freely. "
            "The mark is a label, not a promise, so the Toolbox lists it with your "
            "credits to be safe.",
            credit=CREDIT_LISTED,
            commercial=True,
            changes=True,
            share_alike=False,
            steps=(
                "No credit is required by law, but naming the work and where it came from "
                "is good practice, and the manifest's credits include it.",
                "If it matters, check the source page that the work really is public domain "
                "where you live.",
            ),
            deed_url="https://creativecommons.org/publicdomain/mark/1.0/",
        ),
        LicenseInfo(
            key="by",
            name="CC BY",
            title="Attribution",
            summary="Use it for anything, commercial games included, and change it, as long "
            "as you credit the creator.",
            credit=CREDIT_REQUIRED,
            commercial=True,
            changes=True,
            share_alike=False,
            steps=_HOW_TO_CREDIT,
            deed_url="https://creativecommons.org/licenses/by/4.0/",
        ),
        LicenseInfo(
            key="by-sa",
            name="CC BY-SA",
            title="Attribution-ShareAlike",
            summary="Use and change it, commercially too, with credit. A changed version of "
            "the asset must be shared under the same license.",
            credit=CREDIT_REQUIRED,
            commercial=True,
            changes=True,
            share_alike=True,
            steps=(*_HOW_TO_CREDIT, _SHARE_ALIKE),
            deed_url="https://creativecommons.org/licenses/by-sa/4.0/",
        ),
        LicenseInfo(
            key="by-nd",
            name="CC BY-ND",
            title="Attribution-NoDerivatives",
            summary="Use it commercially with credit, but only as it is: no changed versions.",
            credit=CREDIT_REQUIRED,
            commercial=True,
            changes=False,
            share_alike=False,
            steps=(*_HOW_TO_CREDIT[::2], _NO_CHANGES),
            deed_url="https://creativecommons.org/licenses/by-nd/4.0/",
        ),
        LicenseInfo(
            key="by-nc",
            name="CC BY-NC",
            title="Attribution-NonCommercial",
            summary="Use and change it with credit, but never in anything commercial.",
            credit=CREDIT_REQUIRED,
            commercial=False,
            changes=True,
            share_alike=False,
            steps=(*_HOW_TO_CREDIT, _NONCOMMERCIAL),
            deed_url="https://creativecommons.org/licenses/by-nc/4.0/",
        ),
        LicenseInfo(
            key="by-nc-sa",
            name="CC BY-NC-SA",
            title="Attribution-NonCommercial-ShareAlike",
            summary="Use and change it with credit, never commercially, and share a changed "
            "version under the same license.",
            credit=CREDIT_REQUIRED,
            commercial=False,
            changes=True,
            share_alike=True,
            steps=(*_HOW_TO_CREDIT, _NONCOMMERCIAL, _SHARE_ALIKE),
            deed_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        ),
        LicenseInfo(
            key="by-nc-nd",
            name="CC BY-NC-ND",
            title="Attribution-NonCommercial-NoDerivatives",
            summary="The strictest: credit the creator, never use it commercially, and use it "
            "only as it is.",
            credit=CREDIT_REQUIRED,
            commercial=False,
            changes=False,
            share_alike=False,
            steps=(*_HOW_TO_CREDIT[::2], _NONCOMMERCIAL, _NO_CHANGES),
            deed_url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
        ),
        LicenseInfo(
            key="sampling+",
            name="CC Sampling+",
            title="Sampling Plus (retired)",
            summary="An older license, mostly on Freesound sounds. You may sample and remix "
            "it, commercially too, with credit; the whole work unchanged is for "
            "non-commercial use only, and never in adverts.",
            credit=CREDIT_REQUIRED,
            commercial=None,
            changes=True,
            share_alike=False,
            steps=(
                *_HOW_TO_CREDIT,
                "In a commercial game, use it only cut, layered or transformed into "
                "something new, and never in advertising.",
            ),
            deed_url="https://creativecommons.org/licenses/sampling+/1.0/",
        ),
        LicenseInfo(
            key="nc-sampling+",
            name="CC NC-Sampling+",
            title="NonCommercial Sampling Plus (retired)",
            summary="Like Sampling+, but never commercial: sample and remix it with credit, "
            "in non-commercial projects only.",
            credit=CREDIT_REQUIRED,
            commercial=False,
            changes=True,
            share_alike=False,
            steps=(*_HOW_TO_CREDIT, _NONCOMMERCIAL),
            deed_url="https://creativecommons.org/licenses/nc-sampling+/1.0/",
        ),
        LicenseInfo(
            key="unknown",
            name="Unknown license",
            title="Not stated",
            summary="The provider didn't say. Don't ship it until you've found its license on "
            "the source page.",
            credit=CREDIT_REQUIRED,
            commercial=None,
            changes=None,
            share_alike=False,
            steps=(
                "Open the source page and find the license there.",
                "Until you have, treat it as all rights reserved and leave it out of a release.",
            ),
            deed_url="",
        ),
    )
}

# The guide's order: freest first, retired and unknown last.
LICENSE_ORDER = tuple(LICENSES)

_VERSION = re.compile(r"[\s-]*v?\d+(\.\d+)*$")


def license_key(name: str) -> str:
    """The LICENSES key for a license as a provider wrote it.

    "CC0 1.0" is "cc0", "CC BY-NC-SA 3.0" is "by-nc-sa", "Public Domain Mark"
    is "pdm" and "CC SAMPLING+ 1.0" is "sampling+". Case, spacing, a "CC"
    prefix and a version number don't matter. Anything unrecognised is
    "unknown".
    """
    text = " ".join(name.strip().lower().split())
    if text.startswith("cc0") or text.startswith("cc zero"):
        return "cc0"
    if "public domain" in text or text in ("pdm", "pd"):
        return "pdm"
    body = re.sub(r"^cc[\s-]+", "", text)
    body = _VERSION.sub("", body).replace(" ", "-")
    return body if body in LICENSES else "unknown"


def license_info(name: str) -> LicenseInfo:
    """What the license named `name` (as a provider wrote it) means. Never raises."""
    return LICENSES[license_key(name)]
