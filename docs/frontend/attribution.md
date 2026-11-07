# Attribution center and license partials (templates)

A sidebar entry after Packs (`license` icon, `active_nav="attribution"`)
with its own drop colours. **Monochrome throughout: no type colour on any
of its pages.** Every page is a centred column (`.attribution`, 64 rem).
Server side: [../architecture/exports.md](../architecture/exports.md).

Every page's side panel is `packs/partials/attribution_nav.html`: License
guide, and for members Pack attribution and Asset attribution.

## Pages

- **License guide** (`packs/attribution.html`): for members two
  `.attribution-link` cards, for visitors a sign-in note; **Symbols** (two
  `.symbol-legend`s: the elements, and the uses with the verdict key); **At
  a glance: can I use it?** (a table); **The licenses**, one
  `.license-card` per row (`#license-<key>`, outlined when targeted;
  `.license-card-head` with large symbols, the uses, the facts and terms,
  "How to meet it" folded); **How to credit** and **Optional credits**.
  - **On this page** (`#attribution-toc`): Symbols, At a glance, then the
    licenses folded into one "Licenses" row with a count
    (`#attribution-toc-licenses`, a `.panel-fold`, closed at first,
    remembered as `ax-toc-licenses`), each row with its first symbol; then
    How to credit and Optional credits.
  - The legend's stacked name-over-meaning rule is `.symbol-legend
    li:not(.symbol-legend-key) > span:last-child`. Without the `:not` it
    caught the verdict key and put "Not usable"'s icon above its word.
- **Pack attribution** (`packs/attribution_packs.html`): the member's packs,
  each with license chips and counts, what's owed, warnings, `.use-chip`s
  and a link to its page.
- **A pack's attribution** (`packs/attribution_pack.html`): title,
  "Compiled by …", who owns the assets, View pack page (and Edit in builder
  for the owner), **Restrictions in force**, the compatibility block, the
  notice (`packs/partials/notice_copy.html`, `#attribution-notice`: the
  full notice in a `<pre>` with **Copy the notice** as `btn-primary`, and
  the credit lines with **Copy credit lines**; `data-copy` copies an
  element's text and keeps the button's label), then **License terms** (a
  `.credits-group` per license with every item's credit; the owner also
  gets each asset's page) and the optional acknowledgements. No form
  controls.
- **Asset attribution** (`packs/attribution_assets.html`): a form
  (`#attribution-filters`) with the search and two rows of `.filter-chip`
  checkboxes, **License** (types in the library) and **Credit** (required,
  recommended, optional; disabled at 0), each with a count. It swaps
  `#attribution-assets-results`
  (`packs/partials/attribution_assets_results.html`) on change or typing
  with `hx-push-url`, and submits as a page without JavaScript. Results say
  how many match, with Clear filters; Previous and Next keep the filters.
- **An asset's attribution** (`packs/attribution_asset.html`): thumbnail and
  title, Open in library, View on the provider, the license with facts and
  terms, the credit to show (or the optional acknowledgement), the notice,
  and the member's packs holding it.

## License partials

Never colour alone: every verdict has an icon and words.

- `packs/partials/license_symbols.html`: a license's symbols (`lic-zero`,
  `lic-pd`, `lic-by`, `lic-sa`, `lic-nc`, `lic-nd`, `lic-sampling`,
  `lic-unknown`) named in `aria-label` and `title`; `large=True` boxes them,
  `small` is 13 px. Beside every license name.
- `packs/partials/license_facts.html`: four facts, each with a check, a
  cross or a dash.
- `packs/partials/license_terms.html`: **You may**, **You must**, **You may
  not**, three `.license-terms-col`s, the last with an ink top edge.
- `packs/partials/license_uses.html`: "Can I use it?", three `.use-cell`s
  (`use-commercial`, `use-personal`, `use-internal`) with a check, warning
  or cross and the verdict in words: usable plain, with conditions
  outlined, not usable with an ink top edge, its icon inverted and verdict
  underlined.
- `packs/partials/compatibility.html` (`#pack-compatibility`): when a use
  is blocked, `.compat-warning` (a 4 px ink edge): "This pack may not be
  usable for … use.", the reasons, then "edit the pack" (owner) or "contact
  the owner, <username>" (anyone else); otherwise a line saying it's clear
  or has conditions. Then the pack's three `.use-cell`s. Shown on the pack
  page (above the items), a pack's attribution, and inside the builder's
  `#pack-items`, so each swap rechecks it.
